from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import joblib
from sklearn.pipeline import Pipeline

from mwangaza.probabilistic.continuation_calibration import assert_pre_holdout
from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.ml_sanity_audit import (
    AuditConfig,
    episode_equal_weights,
    fit_hazard,
    predict_hazard_continuation,
)
from mwangaza.probabilistic.survival import (
    HORIZONS,
    PhaseObservation,
    SurvivalRow,
    canonical_json,
)

SCHEMA_VERSION = "mwangaza.drought-continuation-serving-bundle.v1"
SNAPSHOT_SCHEMA_VERSION = "mwangaza.drought-continuation-probability-snapshot.v1"
EXPECTED_AUDIT_RUN_HASH = "sha256:2c2173803f14d7fa77e2d7b64d2742b4817a610ed8d57d4e22c396db2609d666"
EXPECTED_ROUTING_RUN_HASH = (
    "sha256:5981338901de379c9943fd2f30b826d0ede687eccff5489657210476e4e74d39"
)
TARGET = "same_episode_continues"


class ContinuationServingError(RuntimeError):
    """Raised when an experimental serving artifact would be unsafe or ambiguous."""


@dataclass(frozen=True)
class ServingConfig:
    c: float = 0.1
    horizon_days: int = 30
    holdout_cutoff: str = "2024-01-01"
    max_missing_fraction: float = 0.45
    max_out_of_range_fraction: float = 0.5
    min_region_train_rows: int = 1
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.c != 0.1 or self.horizon_days != 30:
            raise ContinuationServingError("hazard configuration must remain frozen from 63B")
        if self.holdout_cutoff != "2024-01-01":
            raise ContinuationServingError("holdout cutoff must remain 2024-01-01")
        if not 0 <= self.max_missing_fraction <= 1:
            raise ContinuationServingError("max_missing_fraction must be between zero and one")
        if not 0 <= self.max_out_of_range_fraction <= 1:
            raise ContinuationServingError("max_out_of_range_fraction must be between zero and one")
        if self.min_region_train_rows < 1:
            raise ContinuationServingError("min_region_train_rows must be positive")


@dataclass(frozen=True)
class AuditEvidence:
    audit_run_hash: str
    routing_run_hash: str
    validation_status: str
    episode_weighted_brier: float
    episode_weighted_brier_skill_score: float
    episode_weighted_ece: float
    bootstrap_delta_brier_lower_95: float
    bootstrap_delta_brier_upper_95: float
    improved_outer_folds: int
    outer_fold_count: int

    def __post_init__(self) -> None:
        if self.audit_run_hash != EXPECTED_AUDIT_RUN_HASH:
            raise ContinuationServingError("63B audit run hash mismatch")
        if self.routing_run_hash != EXPECTED_ROUTING_RUN_HASH:
            raise ContinuationServingError("63 routing run hash mismatch")
        if self.validation_status != "inconclusive":
            raise ContinuationServingError("experimental ML must retain inconclusive status")
        for name in (
            "episode_weighted_brier",
            "episode_weighted_brier_skill_score",
            "episode_weighted_ece",
            "bootstrap_delta_brier_lower_95",
            "bootstrap_delta_brier_upper_95",
        ):
            if not math.isfinite(float(getattr(self, name))):
                raise ContinuationServingError(f"{name} must be finite")
        if self.episode_weighted_brier_skill_score <= 0:
            raise ContinuationServingError("experimental ML requires positive point skill")
        if self.episode_weighted_ece > 0.15:
            raise ContinuationServingError("experimental ML calibration is above limit")
        if self.bootstrap_delta_brier_upper_95 <= 0:
            raise ContinuationServingError("robust evidence must not be relabelled inconclusive")
        if self.improved_outer_folds != 2 or self.outer_fold_count != 3:
            raise ContinuationServingError("63B fold evidence mismatch")


@dataclass(frozen=True)
class HazardServingBundle:
    estimator: Pipeline
    evidence: AuditEvidence
    input_hashes: dict[str, str]
    training_region_rows: dict[str, int]
    numeric_ranges: dict[str, tuple[float, float]]
    trained_through: str
    run_hash: str
    c: float = 0.1
    target: str = TARGET
    horizon_days: int = 30
    schema_version: str = SCHEMA_VERSION


def serving_config_from_mapping(value: Mapping[str, Any]) -> ServingConfig:
    return ServingConfig(**dict(value))


def audit_evidence_from_mapping(value: Mapping[str, Any]) -> AuditEvidence:
    return AuditEvidence(**dict(value))


def freeze_hazard_bundle(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    *,
    evidence: AuditEvidence,
    input_hashes: Mapping[str, str],
    config: ServingConfig | None = None,
) -> HazardServingBundle:
    resolved = config or ServingConfig()
    row_values = tuple(
        row
        for row in rows
        if row.targets.get(resolved.horizon_days) is not None
        and row.period_end < resolved.holdout_cutoff
    )
    episode_values = tuple(
        episode for episode in episodes if episode.valid_to < resolved.holdout_cutoff
    )
    assert_pre_holdout(
        row_values,
        episode_values,
    )
    if not row_values or {int(row.targets[30]) for row in row_values} != {0, 1}:
        raise ContinuationServingError("frozen hazard requires both pre-2024 classes")
    _validate_hashes(input_hashes)
    estimator = fit_hazard(
        row_values,
        resolved.c,
        AuditConfig(
            holdout_cutoff=resolved.holdout_cutoff,
            horizon_days=resolved.horizon_days,
            seed=resolved.seed,
        ),
    )
    region_rows = dict(sorted(Counter(row.region_id for row in row_values).items()))
    numeric_ranges = _numeric_ranges(row_values)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "target": TARGET,
        "horizon_days": resolved.horizon_days,
        "c": resolved.c,
        "trained_through": "2023-12-31",
        "evidence": asdict(evidence),
        "input_hashes": dict(sorted(input_hashes.items())),
        "training_region_rows": region_rows,
        "numeric_ranges": numeric_ranges,
        "training_episode_count": len({row.episode_id for row in row_values}),
        "training_row_count": len(row_values),
        "episode_weight_total": sum(episode_equal_weights(row_values)),
    }
    return HazardServingBundle(
        estimator=estimator,
        evidence=evidence,
        input_hashes=dict(sorted(input_hashes.items())),
        training_region_rows=region_rows,
        numeric_ranges=numeric_ranges,
        trained_through="2023-12-31",
        run_hash=_hash(metadata),
    )


def materialize_probability_snapshot(
    bundle: HazardServingBundle,
    serving_rows: Iterable[SurvivalRow],
    observations: Iterable[PhaseObservation],
    routing: Mapping[str, Any],
    *,
    bundle_sha256: str,
    routing_sha256: str,
    generated_at: str,
    config: ServingConfig | None = None,
) -> dict[str, Any]:
    resolved = config or ServingConfig()
    _validate_bundle(bundle)
    _validate_sha256(bundle_sha256, "bundle_sha256")
    _validate_sha256(routing_sha256, "routing_sha256")
    if routing.get("run_hash") != bundle.evidence.routing_run_hash:
        raise ContinuationServingError("routing evidence run hash mismatch")
    phase_baselines = routing.get("phase_baselines")
    if not isinstance(phase_baselines, Mapping):
        raise ContinuationServingError("routing phase baselines are missing")

    latest_observations = _latest_observations(observations)
    latest_rows = _latest_rows(serving_rows)
    items: list[dict[str, Any]] = []
    for region_id, observation in sorted(latest_observations.items()):
        for horizon in HORIZONS:
            if not observation.active:
                items.append(_not_applicable_item(observation, horizon))
                continue
            row = latest_rows.get(region_id)
            if row is None or not _row_overlaps_observation(row, observation):
                items.append(
                    _active_unavailable_item(
                        observation,
                        horizon,
                        "current_feature_row_unavailable",
                    )
                )
                continue
            estimates = []
            if horizon == 30:
                estimates.append(_ml_estimate(bundle, row, resolved))
            estimates.append(_baseline_estimate(phase_baselines, row, horizon))
            status = (
                "available"
                if any(item["status"] == "available" for item in estimates)
                else "unavailable"
            )
            items.append(
                {
                    "region_id": region_id,
                    "as_of": row.as_of,
                    "horizon_days": horizon,
                    "target": TARGET,
                    "current_drought_status": "active",
                    "current_phase": row.current_phase,
                    "current_trend": row.current_trend,
                    "elapsed_days": row.elapsed_days,
                    "status": status,
                    "reason_codes": [] if status == "available" else ["all_estimates_unavailable"],
                    "estimates": estimates,
                }
            )
    base = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "target": TARGET,
        "artifact": {
            "bundle_run_hash": bundle.run_hash,
            "bundle_sha256": bundle_sha256,
            "audit_run_hash": bundle.evidence.audit_run_hash,
            "routing_run_hash": bundle.evidence.routing_run_hash,
            "routing_sha256": routing_sha256,
        },
        "items": items,
    }
    stable = dict(base)
    stable.pop("generated_at")
    return base | {"snapshot_hash": _hash(stable)}


def load_hazard_bundle(path: Path, expected_sha256: str) -> HazardServingBundle:
    if not path.is_file():
        raise ContinuationServingError("hazard bundle is missing")
    if _sha256(path) != expected_sha256:
        raise ContinuationServingError("hazard bundle hash mismatch")
    try:
        value = joblib.load(path)
    except Exception as exc:
        raise ContinuationServingError("hazard bundle is corrupt") from exc
    if not isinstance(value, HazardServingBundle):
        raise ContinuationServingError("hazard bundle has invalid type")
    _validate_bundle(value)
    return value


def hazard_drivers(
    bundle: HazardServingBundle, row: SurvivalRow, limit: int = 3
) -> list[dict[str, Any]]:
    from mwangaza.probabilistic.ml_sanity_audit import hazard_feature_record

    pipeline = bundle.estimator
    vectorizer = pipeline.named_steps["vectorize"]
    imputer = pipeline.named_steps["impute"]
    scaler = pipeline.named_steps["scale"]
    model = pipeline.named_steps["model"]
    names = vectorizer.get_feature_names_out()
    vectorized = vectorizer.transform([hazard_feature_record(row)])
    imputed = imputer.transform(vectorized)
    names = imputer.get_feature_names_out(names)
    scaled = scaler.transform(imputed)
    contributions = [
        (str(name), -float(value) * float(coefficient))
        for name, value, coefficient in zip(
            names,
            scaled[0],
            model.coef_[0],
            strict=True,
        )
    ]
    result = []
    for name, contribution in sorted(
        contributions,
        key=lambda item: (-abs(item[1]), item[0]),
    )[:limit]:
        result.append(
            {
                "feature": _public_feature_name(name),
                "direction": (
                    "higher_continuation_probability"
                    if contribution >= 0
                    else "lower_continuation_probability"
                ),
                "contribution": round(contribution, 6),
                "method": "logistic_logit_contribution",
                "causal": False,
                "statement": "Association in the experimental model; not a causal effect.",
            }
        )
    return result


def _ml_estimate(
    bundle: HazardServingBundle,
    row: SurvivalRow,
    config: ServingConfig,
) -> dict[str, Any]:
    reasons, quality = _ml_quality(bundle, row, config)
    validation = {
        "status": bundle.evidence.validation_status,
        "episode_weighted_brier": bundle.evidence.episode_weighted_brier,
        "episode_weighted_brier_skill_score": bundle.evidence.episode_weighted_brier_skill_score,
        "episode_weighted_ece": bundle.evidence.episode_weighted_ece,
        "bootstrap_delta_brier_ci95": [
            bundle.evidence.bootstrap_delta_brier_lower_95,
            bundle.evidence.bootstrap_delta_brier_upper_95,
        ],
        "improved_outer_folds": bundle.evidence.improved_outer_folds,
        "outer_fold_count": bundle.evidence.outer_fold_count,
    }
    base = {
        "kind": "experimental_ml_prediction",
        "status": "unavailable" if reasons else "available",
        "probability": None,
        "estimator_kind": "ml",
        "model": "discrete_time_logistic_hazard",
        "experimental": True,
        "operational_use": False,
        "validation": validation,
        "quality": quality,
        "reason_codes": reasons,
        "drivers": [],
        "artifact": {
            "schema_version": bundle.schema_version,
            "run_hash": bundle.run_hash,
            "audit_run_hash": bundle.evidence.audit_run_hash,
            "trained_through": bundle.trained_through,
        },
    }
    if reasons:
        return base
    probability = predict_hazard_continuation(bundle.estimator, (row,))[0]
    return base | {
        "probability": probability,
        "drivers": hazard_drivers(bundle, row),
    }


def _baseline_estimate(
    phase_baselines: Mapping[str, Any], row: SurvivalRow, horizon: int
) -> dict[str, Any]:
    horizon_values = phase_baselines.get(str(horizon))
    phase = horizon_values.get(row.current_phase) if isinstance(horizon_values, Mapping) else None
    if not isinstance(phase, Mapping) or not phase.get("eligible"):
        return {
            "kind": "historical_reference",
            "status": "unavailable",
            "probability": None,
            "estimator_kind": "baseline",
            "model": "phase_survival",
            "experimental": False,
            "operational_use": False,
            "validation": {"status": "historical_reference"},
            "quality": {"status": "insufficient_support"},
            "reason_codes": ["phase_baseline_support_insufficient"],
            "drivers": [],
            "evidence": {
                "current_phase": row.current_phase,
                "elapsed_days": row.elapsed_days,
                "causal": False,
            },
        }
    return {
        "kind": "historical_reference",
        "status": "available",
        "probability": float(phase["probability"]),
        "estimator_kind": "baseline",
        "model": "phase_survival",
        "experimental": False,
        "operational_use": False,
        "validation": {"status": "historical_reference"},
        "quality": {
            "status": "ok",
            "known_count": int(phase["known_count"]),
            "episode_count": int(phase["episode_count"]),
        },
        "reason_codes": [],
        "drivers": [],
        "evidence": {
            "current_phase": row.current_phase,
            "elapsed_days": row.elapsed_days,
            "causal": False,
        },
    }


def _ml_quality(
    bundle: HazardServingBundle,
    row: SurvivalRow,
    config: ServingConfig,
) -> tuple[list[str], dict[str, Any]]:
    reasons = []
    feature_values = tuple(row.features.values())
    missing_count = sum(value is None for value in feature_values)
    missing_fraction = missing_count / len(feature_values) if feature_values else 1.0
    if missing_fraction > config.max_missing_fraction:
        reasons.append("feature_missingness_above_limit")
    region_rows = bundle.training_region_rows.get(row.region_id, 0)
    if region_rows < config.min_region_train_rows:
        reasons.append("region_training_support_insufficient")
    comparable = 0
    outside = 0
    for name, value in row.features.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value is None:
            continue
        bounds = bundle.numeric_ranges.get(name)
        if bounds is None:
            continue
        comparable += 1
        outside += not bounds[0] <= float(value) <= bounds[1]
    out_of_range_fraction = outside / comparable if comparable else 1.0
    if out_of_range_fraction > config.max_out_of_range_fraction:
        reasons.append("feature_drift_above_limit")
    return reasons, {
        "status": "blocked" if reasons else "ok",
        "missing_fraction": missing_fraction,
        "out_of_range_fraction": out_of_range_fraction,
        "region_training_rows": region_rows,
    }


def _numeric_ranges(rows: Sequence[SurvivalRow]) -> dict[str, tuple[float, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for name, value in row.features.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            number = float(value)
            if math.isfinite(number):
                values[name].append(number)
    return {
        name: (min(numbers), max(numbers)) for name, numbers in sorted(values.items()) if numbers
    }


def _latest_observations(
    observations: Iterable[PhaseObservation],
) -> dict[str, PhaseObservation]:
    result: dict[str, PhaseObservation] = {}
    for item in observations:
        current = result.get(item.region_id)
        if current is None or (item.valid_to, item.valid_from, item.label_id) > (
            current.valid_to,
            current.valid_from,
            current.label_id,
        ):
            result[item.region_id] = item
    return result


def _latest_rows(rows: Iterable[SurvivalRow]) -> dict[str, SurvivalRow]:
    result: dict[str, SurvivalRow] = {}
    for row in rows:
        current = result.get(row.region_id)
        if current is None or (row.period_end, row.sample_id) > (
            current.period_end,
            current.sample_id,
        ):
            result[row.region_id] = row
    return result


def _row_overlaps_observation(row: SurvivalRow, observation: PhaseObservation) -> bool:
    period = date.fromisoformat(row.period_end)
    return (
        date.fromisoformat(observation.valid_from)
        <= period
        <= date.fromisoformat(observation.valid_to)
    )


def _not_applicable_item(observation: PhaseObservation, horizon: int) -> dict[str, Any]:
    return {
        "region_id": observation.region_id,
        "as_of": observation.valid_to,
        "horizon_days": horizon,
        "target": TARGET,
        "current_drought_status": "inactive",
        "current_phase": observation.phase,
        "current_trend": observation.trend,
        "elapsed_days": None,
        "status": "not_applicable",
        "reason_codes": ["no_active_official_drought"],
        "estimates": [],
    }


def _active_unavailable_item(
    observation: PhaseObservation, horizon: int, reason: str
) -> dict[str, Any]:
    return {
        "region_id": observation.region_id,
        "as_of": observation.valid_to,
        "horizon_days": horizon,
        "target": TARGET,
        "current_drought_status": "active",
        "current_phase": observation.phase,
        "current_trend": observation.trend,
        "elapsed_days": None,
        "status": "unavailable",
        "reason_codes": [reason],
        "estimates": [],
    }


def _validate_bundle(bundle: HazardServingBundle) -> None:
    if bundle.schema_version != SCHEMA_VERSION or bundle.target != TARGET:
        raise ContinuationServingError("hazard bundle contract mismatch")
    if bundle.horizon_days != 30 or bundle.c != 0.1:
        raise ContinuationServingError("hazard bundle parameters are not frozen")
    if bundle.trained_through != "2023-12-31":
        raise ContinuationServingError("hazard bundle training cutoff mismatch")
    AuditEvidence(**asdict(bundle.evidence))
    _validate_hashes(bundle.input_hashes)


def _validate_hashes(values: Mapping[str, str]) -> None:
    if not values:
        raise ContinuationServingError("input hashes are required")
    for name, value in values.items():
        _validate_sha256(value, name)


def _validate_sha256(value: str, name: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ContinuationServingError(f"{name} must be a complete SHA-256")


def _public_feature_name(value: str) -> str:
    cleaned = value.replace("missingindicator_", "missing:")
    return cleaned[:120]


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


__all__ = [
    "AuditEvidence",
    "ContinuationServingError",
    "EXPECTED_AUDIT_RUN_HASH",
    "EXPECTED_ROUTING_RUN_HASH",
    "HazardServingBundle",
    "SCHEMA_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "ServingConfig",
    "audit_evidence_from_mapping",
    "freeze_hazard_bundle",
    "hazard_drivers",
    "load_hazard_bundle",
    "materialize_probability_snapshot",
    "serving_config_from_mapping",
]

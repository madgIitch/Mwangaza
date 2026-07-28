from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.survival import (
    HORIZONS,
    MONOTONIC_VERSION,
    SurvivalEvaluationError,
    SurvivalRow,
    apply_monotonic_probabilities,
    canonical_json,
)
from mwangaza.probabilistic.survival import _estimator as survival_estimator

SCHEMA_VERSION = "mwangaza.drought-continuation-hybrid-gate.v1"
CALIBRATION_VERSION = "platt-logit-probability-v1"
EXPECTED_HOLDOUT_EVIDENCE_HASH = (
    "sha256:8d0b592d380a77323329f2bc941819bc51fb305ae8e6ed631584d34e7f6ba955"
)


class ContinuationCalibrationError(SurvivalEvaluationError):
    """Raised when calibration or routing would violate the frozen protocol."""


@dataclass(frozen=True)
class HybridGateConfig:
    evaluation_years: tuple[int, ...] = (2021, 2022, 2023)
    holdout_cutoff: str = "2024-01-01"
    ml_horizon_days: int = 30
    baseline_horizons_days: tuple[int, ...] = (60, 90, 180)
    min_known_targets: int = 100
    min_positive_targets: int = 20
    min_negative_targets: int = 20
    min_evaluation_episodes: int = 5
    max_ece: float = 0.15
    min_phase_targets: int = 20
    min_phase_episodes: int = 5
    seed: int = 2026
    holdout_evidence_hash: str = EXPECTED_HOLDOUT_EVIDENCE_HASH

    def __post_init__(self) -> None:
        if not self.evaluation_years or tuple(sorted(self.evaluation_years)) != self.evaluation_years:
            raise ContinuationCalibrationError("evaluation_years must be non-empty and ordered")
        if self.ml_horizon_days in self.baseline_horizons_days:
            raise ContinuationCalibrationError("ML and baseline-only horizons must be disjoint")
        if tuple(sorted(self.baseline_horizons_days)) != self.baseline_horizons_days:
            raise ContinuationCalibrationError("baseline horizons must be ordered")
        if set((self.ml_horizon_days, *self.baseline_horizons_days)) != set(HORIZONS):
            raise ContinuationCalibrationError("hybrid policy must cover 30/60/90/180 days")
        if not 0 <= self.max_ece <= 1:
            raise ContinuationCalibrationError("max_ece must be between zero and one")
        if any(
            value < 1
            for value in (
                self.min_known_targets,
                self.min_positive_targets,
                self.min_negative_targets,
                self.min_evaluation_episodes,
                self.min_phase_targets,
                self.min_phase_episodes,
            )
        ):
            raise ContinuationCalibrationError("support thresholds must be positive")
        if self.holdout_evidence_hash != EXPECTED_HOLDOUT_EVIDENCE_HASH:
            raise ContinuationCalibrationError("holdout evidence hash is immutable")


@dataclass(frozen=True)
class NestedCalibrationFold:
    evaluation_year: int
    base_episode_ids: tuple[str, ...]
    calibration_episode_ids: tuple[str, ...]
    evaluation_episode_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlattParameters:
    coefficient: float
    intercept: float
    version: str = CALIBRATION_VERSION

    def predict(self, probabilities: Iterable[float]) -> list[float]:
        result = []
        for probability in probabilities:
            score = _logit(probability)
            result.append(_sigmoid(self.coefficient * score + self.intercept))
        return result


@dataclass(frozen=True)
class ContinuationModelBundle:
    estimator: Pipeline
    calibrator: PlattParameters
    trained_through: str
    target: str = "same_episode_continues"
    horizon_days: int = 30
    schema_version: str = SCHEMA_VERSION


def build_nested_calibration_folds(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: HybridGateConfig | None = None,
) -> tuple[NestedCalibrationFold, ...]:
    resolved = config or HybridGateConfig()
    row_values = tuple(rows)
    episode_values = tuple(episodes)
    assert_pre_holdout(row_values, episode_values, resolved)
    row_episode_ids = {row.episode_id for row in row_values}
    result = []
    for evaluation_year in resolved.evaluation_years:
        calibration_start = date(evaluation_year - 1, 1, 1)
        evaluation_start = date(evaluation_year, 1, 1)
        evaluation_end = date(evaluation_year + 1, 1, 1)
        base = []
        calibration = []
        evaluation = []
        for episode in episode_values:
            if episode.episode_id not in row_episode_ids:
                continue
            start = date.fromisoformat(episode.valid_from)
            end = date.fromisoformat(episode.valid_to)
            if end < calibration_start:
                base.append(episode.episode_id)
            elif calibration_start <= start and end < evaluation_start:
                calibration.append(episode.episode_id)
            elif evaluation_start <= start and end < evaluation_end:
                evaluation.append(episode.episode_id)
        fold = NestedCalibrationFold(
            evaluation_year=evaluation_year,
            base_episode_ids=tuple(sorted(base)),
            calibration_episode_ids=tuple(sorted(calibration)),
            evaluation_episode_ids=tuple(sorted(evaluation)),
        )
        _assert_fold_disjoint(fold)
        if not fold.base_episode_ids or not fold.calibration_episode_ids or not fold.evaluation_episode_ids:
            raise ContinuationCalibrationError(
                f"nested fold {evaluation_year} lacks base, calibration, or evaluation episodes"
            )
        result.append(fold)
    return tuple(result)


def fit_platt_calibrator(
    probabilities: Iterable[float], targets: Iterable[int], *, seed: int = 2026
) -> PlattParameters:
    probability_values = tuple(float(value) for value in probabilities)
    target_values = tuple(int(value) for value in targets)
    if len(probability_values) != len(target_values) or not probability_values:
        raise ContinuationCalibrationError("Platt inputs must be non-empty and aligned")
    if set(target_values) != {0, 1}:
        raise ContinuationCalibrationError("Platt calibration requires both classes")
    estimator = LogisticRegression(random_state=seed, solver="lbfgs", max_iter=1000)
    estimator.fit([[_logit(value)] for value in probability_values], target_values)
    return PlattParameters(
        coefficient=float(estimator.coef_[0][0]),
        intercept=float(estimator.intercept_[0]),
    )


def evaluate_hybrid_continuation(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    *,
    input_hashes: Mapping[str, str],
    config: HybridGateConfig | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    resolved = config or HybridGateConfig()
    row_values = tuple(rows)
    episode_values = tuple(episodes)
    _validate_hashes(input_hashes)
    folds = build_nested_calibration_folds(row_values, episode_values, resolved)
    by_episode = _rows_by_episode(row_values)
    oof = []
    for number, fold in enumerate(folds, 1):
        base = _known_rows(by_episode, fold.base_episode_ids, resolved.ml_horizon_days)
        calibration = _known_rows(
            by_episode, fold.calibration_episode_ids, resolved.ml_horizon_days
        )
        evaluation = _known_rows(
            by_episode, fold.evaluation_episode_ids, resolved.ml_horizon_days
        )
        _require_binary_support(base, f"base:{fold.evaluation_year}")
        _require_binary_support(calibration, f"calibration:{fold.evaluation_year}")
        _require_binary_support(evaluation, f"evaluation:{fold.evaluation_year}")
        estimator = _fit_hgb(base, resolved)
        raw_calibration = _predict_hgb(estimator, calibration)
        calibrator = fit_platt_calibrator(
            raw_calibration,
            (int(row.targets[resolved.ml_horizon_days]) for row in calibration),
            seed=resolved.seed,
        )
        raw_evaluation = _predict_hgb(estimator, evaluation)
        calibrated_evaluation = calibrator.predict(raw_evaluation)
        baseline_evaluation = _phase_predictions(
            (*base, *calibration), evaluation, resolved.ml_horizon_days
        )
        for row, raw, calibrated, baseline in zip(
            evaluation,
            raw_evaluation,
            calibrated_evaluation,
            baseline_evaluation,
            strict=True,
        ):
            oof.append(
                {
                    "evaluation_year": fold.evaluation_year,
                    "sample_id": row.sample_id,
                    "episode_id": row.episode_id,
                    "region_id": row.region_id,
                    "as_of": row.as_of,
                    "horizon_days": resolved.ml_horizon_days,
                    "actual": int(row.targets[resolved.ml_horizon_days]),
                    "hgb_probability": raw,
                    "calibrated_probability": calibrated,
                    "baseline_probability": baseline,
                }
            )
        if progress:
            progress(number, len(folds))

    baseline_metrics = probability_metrics(oof, "baseline_probability")
    raw_metrics = probability_metrics(oof, "hgb_probability", baseline_metrics)
    calibrated_metrics = probability_metrics(
        oof, "calibrated_probability", baseline_metrics
    )
    gate_status, gate_reasons = hybrid_ml_gate(
        calibrated_metrics, raw_metrics, input_hashes, resolved
    )
    phase_baselines = build_phase_baselines(row_values, resolved)
    global_routes = build_global_routes(
        gate_status,
        gate_reasons,
        calibrated_metrics,
        phase_baselines,
        input_hashes,
        resolved,
    )
    regional_routes = build_regional_routes(
        oof, gate_status, phase_baselines, row_values, resolved
    )
    folds_payload = [asdict(item) for item in folds]
    base_payload = {
        "schema_version": SCHEMA_VERSION,
        "target": "same_episode_continues",
        "config": asdict(resolved),
        "input_hashes": dict(sorted(input_hashes.items())),
        "folds": folds_payload,
        "metrics": {
            "phase_survival": baseline_metrics,
            "hist_gradient_boosting": raw_metrics,
            "hist_gradient_boosting_platt": calibrated_metrics,
        },
        "global_routes": global_routes,
        "regional_routes": regional_routes,
        "phase_baselines": phase_baselines,
        "oof_sha256": _hash(oof),
        "holdout_policy": {
            "cutoff": resolved.holdout_cutoff,
            "evidence_hash": resolved.holdout_evidence_hash,
            "used_for_fit_calibration_or_gate": False,
        },
    }
    return {
        **base_payload,
        "run_hash": _hash(base_payload),
        "oof_predictions": oof,
        "model_bundle": (
            fit_final_bundle(row_values, episode_values, resolved)
            if gate_status == "ml_experimental"
            else None
        ),
    }


def probability_metrics(
    rows: Iterable[Mapping[str, Any]],
    probability_field: str,
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = tuple(rows)
    if not values:
        raise ContinuationCalibrationError("probability metrics require rows")
    probabilities = [_bounded(float(row[probability_field])) for row in values]
    targets = [int(row["actual"]) for row in values]
    brier = sum((probability - target) ** 2 for probability, target in zip(probabilities, targets, strict=True)) / len(values)
    log_loss = -sum(
        target * math.log(_clip(probability))
        + (1 - target) * math.log(_clip(1 - probability))
        for probability, target in zip(probabilities, targets, strict=True)
    ) / len(values)
    bins = _calibration_bins(probabilities, targets)
    ece = sum(
        item["count"] / len(values)
        * abs(float(item["mean_probability"]) - float(item["observed_frequency"]))
        for item in bins
        if item["count"]
    )
    baseline_brier = float(baseline["brier_score"]) if baseline else brier
    return {
        "probability_field": probability_field,
        "known_count": len(values),
        "positive_count": sum(targets),
        "negative_count": len(values) - sum(targets),
        "episode_count": len({str(row["episode_id"]) for row in values}),
        "region_count": len({str(row["region_id"]) for row in values}),
        "brier_score": brier,
        "baseline_brier_score": baseline_brier,
        "brier_skill_score": 0.0 if baseline is None else 1 - brier / baseline_brier,
        "log_loss": log_loss,
        "ece": ece,
        "calibration_bins": bins,
    }


def hybrid_ml_gate(
    calibrated: Mapping[str, Any],
    raw: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    config: HybridGateConfig | None = None,
) -> tuple[str, list[str]]:
    resolved = config or HybridGateConfig()
    reasons = []
    if int(calibrated["known_count"]) < resolved.min_known_targets:
        reasons.append("insufficient_known_targets")
    if int(calibrated["positive_count"]) < resolved.min_positive_targets:
        reasons.append("insufficient_positive_targets")
    if int(calibrated["negative_count"]) < resolved.min_negative_targets:
        reasons.append("insufficient_negative_targets")
    if int(calibrated["episode_count"]) < resolved.min_evaluation_episodes:
        reasons.append("insufficient_evaluation_episodes")
    if float(calibrated["brier_skill_score"]) <= 0:
        reasons.append("non_positive_brier_skill")
    if float(calibrated["brier_score"]) > float(raw["brier_score"]):
        reasons.append("calibration_worsens_brier")
    if float(calibrated["ece"]) > resolved.max_ece:
        reasons.append("calibration_error_above_limit")
    try:
        _validate_hashes(input_hashes)
    except ContinuationCalibrationError:
        reasons.append("invalid_input_hash")
    return ("ml_experimental", []) if not reasons else ("baseline", sorted(set(reasons)))


def build_phase_baselines(
    rows: Iterable[SurvivalRow], config: HybridGateConfig | None = None
) -> dict[str, dict[str, dict[str, Any]]]:
    resolved = config or HybridGateConfig()
    result: dict[str, dict[str, dict[str, Any]]] = {}
    raw: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for horizon in HORIZONS:
        by_phase: dict[str, list[SurvivalRow]] = defaultdict(list)
        for row in rows:
            if row.targets[horizon] is not None:
                by_phase[row.current_phase].append(row)
        for phase, values in sorted(by_phase.items()):
            probability = sum(int(row.targets[horizon]) for row in values) / len(values)
            episode_count = len({row.episode_id for row in values})
            raw[horizon][phase] = {
                "probability": probability,
                "known_count": len(values),
                "episode_count": episode_count,
                "eligible": len(values) >= resolved.min_phase_targets
                and episode_count >= resolved.min_phase_episodes,
            }
    phases = sorted({phase for values in raw.values() for phase in values})
    for phase in phases:
        available = {
            horizon: float(raw[horizon][phase]["probability"])
            for horizon in HORIZONS
            if phase in raw[horizon]
        }
        if len(available) != len(HORIZONS):
            continue
        monotonic = apply_monotonic_probabilities(available)
        for horizon in HORIZONS:
            result.setdefault(str(horizon), {})[phase] = {
                **raw[horizon][phase],
                "probability": monotonic[horizon],
                "monotonic_version": MONOTONIC_VERSION,
            }
    return result


def build_global_routes(
    gate_status: str,
    gate_reasons: Iterable[str],
    calibrated_metrics: Mapping[str, Any],
    phase_baselines: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    config: HybridGateConfig,
) -> list[dict[str, Any]]:
    routes = []
    ml_available = gate_status == "ml_experimental"
    for horizon in HORIZONS:
        if horizon == config.ml_horizon_days and ml_available:
            routes.append(
                {
                    "horizon_days": horizon,
                    "target": "same_episode_continues",
                    "status": "ml_experimental",
                    "candidate": "hist_gradient_boosting_platt",
                    "estimator_kind": "ml",
                    "experimental": True,
                    "fallback_reason": None,
                    "reason_codes": [],
                    "brier_skill_score": calibrated_metrics["brier_skill_score"],
                    "metrics": dict(calibrated_metrics),
                    "support_by_phase": phase_baselines.get(str(horizon), {}),
                    "versions": {
                        "schema": SCHEMA_VERSION,
                        "calibration": CALIBRATION_VERSION,
                    },
                    "input_hashes": dict(sorted(input_hashes.items())),
                }
            )
            continue
        baseline_available = _has_eligible_phase_baseline(phase_baselines, horizon)
        reasons = list(gate_reasons) if horizon == config.ml_horizon_days else []
        routes.append(
            {
                "horizon_days": horizon,
                "target": "same_episode_continues",
                "status": "baseline" if baseline_available else "unavailable",
                "candidate": "phase_survival" if baseline_available else None,
                "estimator_kind": "baseline" if baseline_available else "none",
                "experimental": False,
                "fallback_reason": (
                    "ml_gate_failed" if horizon == config.ml_horizon_days and reasons else None
                ),
                "reason_codes": reasons if reasons else ([] if baseline_available else ["baseline_support_insufficient"]),
                "brier_skill_score": 0.0 if baseline_available else None,
                "metrics": (
                    dict(calibrated_metrics)
                    if horizon == config.ml_horizon_days
                    else {"brier_skill_score": 0.0}
                ),
                "support_by_phase": phase_baselines.get(str(horizon), {}),
                "versions": {
                    "schema": SCHEMA_VERSION,
                    "monotonic": MONOTONIC_VERSION,
                },
                "input_hashes": dict(sorted(input_hashes.items())),
            }
        )
    return routes


def build_regional_routes(
    oof: Iterable[Mapping[str, Any]],
    gate_status: str,
    phase_baselines: Mapping[str, Any],
    rows: Iterable[SurvivalRow],
    config: HybridGateConfig,
) -> list[dict[str, Any]]:
    by_region: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in oof:
        by_region[str(item["region_id"])].append(item)
    regions = sorted({row.region_id for row in rows})
    result = []
    for region in regions:
        values = by_region.get(region, [])
        targets = [int(item["actual"]) for item in values]
        regional_ml = gate_status == "ml_experimental" and set(targets) == {0, 1}
        for horizon in HORIZONS:
            baseline_available = _has_eligible_phase_baseline(phase_baselines, horizon)
            if horizon == config.ml_horizon_days and regional_ml:
                candidate = "hist_gradient_boosting_platt"
                estimator_kind = "ml"
                reason_codes: list[str] = []
            elif baseline_available:
                candidate = "phase_survival"
                estimator_kind = "baseline"
                reason_codes = (
                    ["regional_ml_support_insufficient"]
                    if horizon == config.ml_horizon_days
                    else []
                )
            else:
                candidate = None
                estimator_kind = "none"
                reason_codes = ["baseline_support_insufficient"]
            result.append(
                {
                    "region_id": region,
                    "horizon_days": horizon,
                    "status": (
                        "ml_experimental"
                        if estimator_kind == "ml"
                        else "baseline" if estimator_kind == "baseline" else "unavailable"
                    ),
                    "candidate": candidate,
                    "estimator_kind": estimator_kind,
                    "experimental": estimator_kind == "ml",
                    "known_oof_count": len(targets) if horizon == config.ml_horizon_days else None,
                    "positive_oof_count": sum(targets) if horizon == config.ml_horizon_days else None,
                    "negative_oof_count": len(targets) - sum(targets) if horizon == config.ml_horizon_days else None,
                    "reason_codes": reason_codes,
                }
            )
    return result


def fit_final_bundle(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: HybridGateConfig | None = None,
) -> ContinuationModelBundle:
    resolved = config or HybridGateConfig()
    row_values = tuple(rows)
    episode_values = tuple(episodes)
    assert_pre_holdout(row_values, episode_values, resolved)
    by_episode = _rows_by_episode(row_values)
    base_ids = tuple(
        episode.episode_id
        for episode in episode_values
        if date.fromisoformat(episode.valid_to) < date(2023, 1, 1)
    )
    calibration_ids = tuple(
        episode.episode_id
        for episode in episode_values
        if date(2023, 1, 1) <= date.fromisoformat(episode.valid_from)
        and date.fromisoformat(episode.valid_to) < date(2024, 1, 1)
    )
    base = _known_rows(by_episode, base_ids, resolved.ml_horizon_days)
    calibration = _known_rows(by_episode, calibration_ids, resolved.ml_horizon_days)
    _require_binary_support(base, "final_base")
    _require_binary_support(calibration, "final_calibration")
    estimator = _fit_hgb(base, resolved)
    calibrator = fit_platt_calibrator(
        _predict_hgb(estimator, calibration),
        (int(row.targets[resolved.ml_horizon_days]) for row in calibration),
        seed=resolved.seed,
    )
    return ContinuationModelBundle(estimator, calibrator, "2023-12-31")


def load_continuation_model_bundle(
    path: Path, expected_sha256: str
) -> ContinuationModelBundle:
    if not path.is_file():
        raise ContinuationCalibrationError("continuation model artifact is missing")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 != f"sha256:{digest}":
        raise ContinuationCalibrationError("continuation model artifact hash mismatch")
    try:
        value = joblib.load(path)
    except Exception as exc:
        raise ContinuationCalibrationError("continuation model artifact is corrupt") from exc
    if not isinstance(value, ContinuationModelBundle):
        raise ContinuationCalibrationError("continuation model artifact has invalid type")
    if value.target != "same_episode_continues" or value.horizon_days != 30:
        raise ContinuationCalibrationError("continuation model artifact contract mismatch")
    return value


def assert_pre_holdout(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: HybridGateConfig | None = None,
) -> None:
    cutoff = date.fromisoformat((config or HybridGateConfig()).holdout_cutoff)
    future_row = next(
        (row for row in rows if date.fromisoformat(row.period_end) >= cutoff), None
    )
    if future_row:
        raise ContinuationCalibrationError(
            f"holdout row forbidden in calibration: {future_row.sample_id}"
        )
    future_episode = next(
        (episode for episode in episodes if date.fromisoformat(episode.valid_to) >= cutoff),
        None,
    )
    if future_episode:
        raise ContinuationCalibrationError(
            f"holdout episode forbidden in calibration: {future_episode.episode_id}"
        )


def config_from_mapping(value: Mapping[str, Any]) -> HybridGateConfig:
    payload = dict(value)
    for name in ("evaluation_years", "baseline_horizons_days"):
        if name in payload:
            payload[name] = tuple(int(item) for item in payload[name])
    return HybridGateConfig(**payload)


def _fit_hgb(rows: Iterable[SurvivalRow], config: HybridGateConfig) -> Pipeline:
    values = tuple(rows)
    estimator = survival_estimator("hist_gradient_boosting", config.seed)
    estimator.fit(
        [row.features for row in values],
        [int(row.targets[config.ml_horizon_days]) for row in values],
    )
    return estimator


def _predict_hgb(estimator: Pipeline, rows: Iterable[SurvivalRow]) -> list[float]:
    values = tuple(rows)
    return [float(item[1]) for item in estimator.predict_proba([row.features for row in values])]


def _phase_predictions(
    train: Iterable[SurvivalRow], test: Iterable[SurvivalRow], horizon: int
) -> list[float]:
    by_phase: dict[str, list[int]] = defaultdict(list)
    all_targets = []
    for row in train:
        target = row.targets[horizon]
        if target is not None:
            by_phase[row.current_phase].append(int(target))
            all_targets.append(int(target))
    if not all_targets:
        raise ContinuationCalibrationError("phase baseline has no known targets")
    frequency = sum(all_targets) / len(all_targets)
    return [
        sum(by_phase[row.current_phase]) / len(by_phase[row.current_phase])
        if by_phase[row.current_phase]
        else frequency
        for row in test
    ]


def _known_rows(
    rows_by_episode: Mapping[str, tuple[SurvivalRow, ...]],
    episode_ids: Iterable[str],
    horizon: int,
) -> tuple[SurvivalRow, ...]:
    return tuple(
        sorted(
            (
                row
                for episode_id in episode_ids
                for row in rows_by_episode.get(episode_id, ())
                if row.targets[horizon] is not None
            ),
            key=lambda row: (row.period_end, row.region_id, row.sample_id),
        )
    )


def _rows_by_episode(rows: Iterable[SurvivalRow]) -> dict[str, tuple[SurvivalRow, ...]]:
    result: dict[str, list[SurvivalRow]] = defaultdict(list)
    for row in rows:
        result[row.episode_id].append(row)
    return {key: tuple(values) for key, values in result.items()}


def _require_binary_support(rows: Iterable[SurvivalRow], name: str) -> None:
    values = tuple(int(row.targets[30]) for row in rows if row.targets[30] is not None)
    if set(values) != {0, 1}:
        raise ContinuationCalibrationError(f"{name} requires both target classes")


def _assert_fold_disjoint(fold: NestedCalibrationFold) -> None:
    groups = (
        set(fold.base_episode_ids),
        set(fold.calibration_episode_ids),
        set(fold.evaluation_episode_ids),
    )
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        raise ContinuationCalibrationError(
            f"episode leakage in nested fold {fold.evaluation_year}"
        )


def _validate_hashes(values: Mapping[str, str]) -> None:
    if not values or any(
        not str(value).startswith("sha256:") or len(str(value)) != 71
        for value in values.values()
    ):
        raise ContinuationCalibrationError("input hashes must be complete SHA-256 values")


def _has_eligible_phase_baseline(
    phase_baselines: Mapping[str, Any], horizon: int
) -> bool:
    return any(
        bool(value.get("eligible"))
        for value in phase_baselines.get(str(horizon), {}).values()
    )


def _calibration_bins(
    probabilities: list[float], targets: list[int]
) -> list[dict[str, Any]]:
    result = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        indexes = [
            index
            for index, probability in enumerate(probabilities)
            if lower <= probability < upper or (upper == 1.0 and probability == 1.0)
        ]
        result.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(indexes),
                "mean_probability": (
                    sum(probabilities[index] for index in indexes) / len(indexes)
                    if indexes
                    else None
                ),
                "observed_frequency": (
                    sum(targets[index] for index in indexes) / len(indexes)
                    if indexes
                    else None
                ),
            }
        )
    return result


def _bounded(value: float) -> float:
    if not math.isfinite(value):
        raise ContinuationCalibrationError("non-finite probability")
    return min(1.0, max(0.0, value))


def _clip(value: float) -> float:
    return min(1 - 1e-15, max(1e-15, value))


def _logit(value: float) -> float:
    probability = _clip(_bounded(float(value)))
    return math.log(probability / (1 - probability))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


def _hash(value: object) -> str:
    digest = hashlib.sha256(canonical_json(value).encode()).hexdigest()
    return f"sha256:{digest}"


__all__ = [
    "CALIBRATION_VERSION",
    "ContinuationCalibrationError",
    "ContinuationModelBundle",
    "EXPECTED_HOLDOUT_EVIDENCE_HASH",
    "HybridGateConfig",
    "NestedCalibrationFold",
    "PlattParameters",
    "assert_pre_holdout",
    "build_global_routes",
    "build_nested_calibration_folds",
    "build_phase_baselines",
    "build_regional_routes",
    "config_from_mapping",
    "evaluate_hybrid_continuation",
    "fit_final_bundle",
    "fit_platt_calibrator",
    "hybrid_ml_gate",
    "load_continuation_model_bundle",
    "probability_metrics",
]

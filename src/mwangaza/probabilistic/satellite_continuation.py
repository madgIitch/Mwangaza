from __future__ import annotations

import bisect
import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

from sklearn.feature_extraction import DictVectorizer  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from mwangaza.probabilistic.survival import canonical_json

TARGET = "observed_drought_condition_continues"
STATE_VERSION = "satellite-multisignal-hysteresis-v1"
BUNDLE_SCHEMA_VERSION = "mwangaza.satellite-continuation-bundle.v1"
SNAPSHOT_SCHEMA_VERSION = "mwangaza.drought-continuation-probability-snapshot.v1"
CORE_SIGNALS = (
    "spi_3m",
    "spei_3m",
    "ndvi_anomaly",
    "ndvi_decline_persistence_dekads",
    "ndvi_slope_3dekad",
    "soil_moisture_rootzone",
)


class SatelliteContinuationError(RuntimeError):
    """Raised when all-ADM1 continuation would be incomplete or temporally unsafe."""


@dataclass(frozen=True)
class SatelliteConditionConfig:
    reference_end: str = "2020-12-31"
    state_start: str = "2021-01-01"
    training_cutoff: str = "2024-01-01"
    activation_consecutive_dekads: int = 2
    recovery_consecutive_dekads: int = 2
    meteorological_threshold: float = -0.8
    ndvi_anomaly_threshold: float = -0.02
    ndvi_persistence_dekads: int = 2
    soil_moisture_percentile: float = 0.2
    soil_reference_minimum: int = 12
    max_signal_age_days: dict[str, int] | None = None
    horizons_days: tuple[int, ...] = (30, 60, 90, 180)
    elapsed_bin_days: int = 30
    ml_horizon_days: int = 30
    ml_min_backtest_rows: int = 50
    ml_max_ece: float = 0.15
    seed: int = 2026

    def __post_init__(self) -> None:
        if self.activation_consecutive_dekads < 1 or self.recovery_consecutive_dekads < 1:
            raise SatelliteContinuationError("hysteresis windows must be positive")
        if not 0 < self.soil_moisture_percentile < 1:
            raise SatelliteContinuationError("soil percentile must be between zero and one")
        if tuple(self.horizons_days) != (30, 60, 90, 180):
            raise SatelliteContinuationError("continuation horizons must be 30, 60, 90 and 180")
        if self.ml_horizon_days != 30:
            raise SatelliteContinuationError("experimental ML remains limited to 30 days")
        if date.fromisoformat(self.reference_end) >= date.fromisoformat(self.training_cutoff):
            raise SatelliteContinuationError("reference period must precede training cutoff")


@dataclass(frozen=True)
class SatelliteStatePoint:
    region_id: str
    parent_iso3: str
    period_end: str
    as_of: str
    raw_condition: bool | None
    active: bool
    episode_id: str | None
    episode_start: str | None
    elapsed_days: int | None
    trend: str
    family_states: dict[str, bool | None]
    signal_freshness: dict[str, dict[str, Any]]
    features: dict[str, float | str | None]


@dataclass(frozen=True)
class SatelliteSample:
    sample_id: str
    episode_id: str
    region_id: str
    as_of: str
    period_end: str
    elapsed_days: int
    features: dict[str, float | str | None]
    targets: dict[int, int | None]


@dataclass(frozen=True)
class SatelliteServingBundle:
    estimator: Pipeline | None
    baselines: dict[str, dict[str, Any]]
    validation: dict[str, Any]
    input_hashes: dict[str, str]
    numeric_ranges: dict[str, tuple[float, float]]
    training_regions: tuple[str, ...]
    training_row_count: int
    trained_through: str
    config: dict[str, Any]
    run_hash: str
    target: str = TARGET
    state_version: str = STATE_VERSION
    schema_version: str = BUNDLE_SCHEMA_VERSION


def config_from_mapping(value: Mapping[str, Any]) -> SatelliteConditionConfig:
    payload = dict(value)
    payload.pop("schema_version", None)
    payload["horizons_days"] = tuple(payload.get("horizons_days", (30, 60, 90, 180)))
    payload["max_signal_age_days"] = {
        str(name): int(days)
        for name, days in dict(payload.get("max_signal_age_days") or {}).items()
    }
    return SatelliteConditionConfig(**payload)


def load_feature_payloads(path: Path) -> tuple[dict[str, Any], ...]:
    source = path / "adm1-features.jsonl" if path.is_dir() else path
    if not source.is_file():
        raise SatelliteContinuationError("ADM1 feature artifact is missing")
    result: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise SatelliteContinuationError(f"invalid ADM1 feature row {number}") from exc
            if not isinstance(payload.get("signals"), dict):
                raise SatelliteContinuationError(f"ADM1 feature row {number} has no signals")
            result.append(payload)
    return tuple(result)


def derive_satellite_states(
    payloads: Iterable[Mapping[str, Any]],
    config: SatelliteConditionConfig,
    *,
    expected_region_ids: Iterable[str] | None = None,
) -> tuple[SatelliteStatePoint, ...]:
    rows = tuple(payloads)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for payload in rows:
        grouped[str(payload["region_id"])].append(payload)
    expected = set(expected_region_ids or grouped)
    if set(grouped) != expected:
        missing = sorted(expected - set(grouped))
        extra = sorted(set(grouped) - expected)
        raise SatelliteContinuationError(
            f"ADM1 catalog mismatch: missing={len(missing)} extra={len(extra)}"
        )
    soil_reference = _soil_reference(rows, config)
    state_start = date.fromisoformat(config.state_start)
    result: list[SatelliteStatePoint] = []
    for region_id in sorted(grouped):
        ordered = sorted(grouped[region_id], key=lambda item: str(item["period_end"]))
        active = False
        stress_run = 0
        recovery_run = 0
        episode_start: str | None = None
        episode_id: str | None = None
        previous_raw: bool | None = None
        for row_index, payload in enumerate(ordered):
            period_end = str(payload["period_end"])
            raw, families, freshness = _condition(payload, soil_reference, config)
            if raw is True:
                stress_run += 1
                recovery_run = 0
            elif raw is False:
                recovery_run += 1
                stress_run = 0
            else:
                stress_run = 0
                recovery_run = 0
            if not active and stress_run >= config.activation_consecutive_dekads:
                active = True
                start_index = max(0, row_index - config.activation_consecutive_dekads + 1)
                episode_start = str(ordered[start_index]["period_end"])
                episode_id = _episode_id(region_id, episode_start)
            elif active and recovery_run >= config.recovery_consecutive_dekads:
                active = False
                episode_start = None
                episode_id = None
            trend = _trend(raw, previous_raw, active)
            previous_raw = raw
            if date.fromisoformat(period_end) < state_start:
                continue
            elapsed = (
                (date.fromisoformat(period_end) - date.fromisoformat(episode_start)).days
                if active and episode_start
                else None
            )
            result.append(
                SatelliteStatePoint(
                    region_id=region_id,
                    parent_iso3=str(payload.get("parent_iso3") or "unknown"),
                    period_end=period_end,
                    as_of=str(payload["as_of"]),
                    raw_condition=raw,
                    active=active,
                    episode_id=episode_id,
                    episode_start=episode_start,
                    elapsed_days=elapsed,
                    trend=trend,
                    family_states=families,
                    signal_freshness=freshness,
                    features=_features(payload, families, elapsed),
                )
            )
    latest = _latest_states(result)
    if set(latest) != expected:
        raise SatelliteContinuationError("not every ADM1 has a current satellite evaluation")
    unknown = sorted(region for region, point in latest.items() if point.raw_condition is None)
    if unknown:
        raise SatelliteContinuationError(
            f"current satellite condition is indeterminate for {len(unknown)} ADM1"
        )
    return tuple(result)


def build_satellite_samples(
    states: Iterable[SatelliteStatePoint],
    horizons: Sequence[int] = (30, 60, 90, 180),
) -> tuple[SatelliteSample, ...]:
    grouped: dict[str, list[SatelliteStatePoint]] = defaultdict(list)
    for point in states:
        grouped[point.region_id].append(point)
    result: list[SatelliteSample] = []
    for region_id in sorted(grouped):
        ordered = sorted(grouped[region_id], key=lambda item: item.period_end)
        dates = [date.fromisoformat(item.period_end) for item in ordered]
        for point in ordered:
            if not point.active or not point.episode_id or point.elapsed_days is None:
                continue
            targets: dict[int, int | None] = {}
            current_date = date.fromisoformat(point.period_end)
            for horizon in horizons:
                index = bisect.bisect_left(dates, current_date + timedelta(days=horizon))
                future = ordered[index] if index < len(ordered) else None
                targets[int(horizon)] = (
                    None
                    if future is None
                    else int(future.active and future.episode_id == point.episode_id)
                )
            identity = f"{region_id}:{point.period_end}:{point.episode_id}"
            result.append(
                SatelliteSample(
                    sample_id=f"satellite:{hashlib.sha256(identity.encode()).hexdigest()[:20]}",
                    episode_id=point.episode_id,
                    region_id=region_id,
                    as_of=point.as_of,
                    period_end=point.period_end,
                    elapsed_days=point.elapsed_days,
                    features=point.features,
                    targets=targets,
                )
            )
    return tuple(result)


def freeze_satellite_bundle(
    samples: Iterable[SatelliteSample],
    *,
    input_hashes: Mapping[str, str],
    config: SatelliteConditionConfig,
) -> SatelliteServingBundle:
    values = tuple(samples)
    cutoff = date.fromisoformat(config.training_cutoff)
    training = tuple(
        row
        for row in values
        if row.targets.get(config.ml_horizon_days) is not None
        and date.fromisoformat(row.period_end) + timedelta(days=config.ml_horizon_days) < cutoff
    )
    if not training:
        raise SatelliteContinuationError("satellite continuation has no pre-cutoff training rows")
    baselines = _fit_baselines(training, config)
    validation = _walk_forward_validation(values, config)
    targets = [int(cast(int, row.targets[config.ml_horizon_days])) for row in training]
    estimator = _fit_estimator(training, config) if set(targets) == {0, 1} else None
    metadata = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "target": TARGET,
        "state_version": STATE_VERSION,
        "training_cutoff": config.training_cutoff,
        "training_rows": len(training),
        "training_regions": sorted({row.region_id for row in training}),
        "baselines": baselines,
        "validation": validation,
        "input_hashes": dict(sorted(input_hashes.items())),
        "config": asdict(config),
    }
    return SatelliteServingBundle(
        estimator=estimator,
        baselines=baselines,
        validation=validation,
        input_hashes=dict(sorted(input_hashes.items())),
        numeric_ranges=_numeric_ranges(training),
        training_regions=tuple(sorted({row.region_id for row in training})),
        training_row_count=len(training),
        trained_through=(cutoff - timedelta(days=1)).isoformat(),
        config=asdict(config),
        run_hash=_hash(metadata),
    )


def materialize_satellite_snapshot(
    bundle: SatelliteServingBundle,
    states: Iterable[SatelliteStatePoint],
    *,
    generated_at: str,
    bundle_sha256: str,
    expected_region_ids: Iterable[str],
    external_validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    latest = _latest_states(states)
    expected = set(expected_region_ids)
    if set(latest) != expected or len(expected) != 121:
        raise SatelliteContinuationError("serving requires exactly 121 current ADM1 states")
    items: list[dict[str, Any]] = []
    for region_id in sorted(expected):
        point = latest[region_id]
        probabilities = _baseline_probabilities(bundle, point)
        for horizon in (30, 60, 90, 180):
            if not point.active:
                items.append(_inactive_item(point, horizon))
                continue
            estimates: list[dict[str, Any]] = []
            if horizon == 30:
                estimates.append(_ml_estimate(bundle, point))
            estimates.append(_baseline_estimate(bundle, point, horizon, probabilities[horizon]))
            if not any(item["status"] == "available" for item in estimates):
                raise SatelliteContinuationError(
                    f"active ADM1 has no continuation probability: {region_id}:{horizon}"
                )
            items.append(_active_item(point, horizon, estimates))
    if len(items) != 484:
        raise SatelliteContinuationError("serving snapshot must contain 121 x 4 items")
    analysis_as_of = max(point.period_end for point in latest.values())
    base = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "query_generated_at": generated_at,
        "analysis_as_of": analysis_as_of,
        "target": TARGET,
        "is_demo": False,
        "coverage": {
            "adm1_count": len(expected),
            "kenya_adm1_count": sum(region.startswith("adm1-ke-") for region in expected),
            "result_count": len(items),
        },
        "artifact": {
            "bundle_run_hash": bundle.run_hash,
            "bundle_sha256": bundle_sha256,
            "state_version": STATE_VERSION,
            "target": TARGET,
            "external_validation": dict(external_validation or {}),
            "fews_role": "acute_food_insecurity_impact_only",
        },
        "items": items,
    }
    stable = dict(base)
    stable.pop("generated_at")
    stable.pop("query_generated_at")
    return base | {"snapshot_hash": _hash(stable)}


def validate_against_ndma(
    states: Iterable[SatelliteStatePoint], label_path: Path
) -> dict[str, Any]:
    source = label_path / "independent-labels.jsonl" if label_path.is_dir() else label_path
    if not source.is_file():
        return {"status": "unavailable", "role": "external_validation_only"}
    grouped: dict[str, list[SatelliteStatePoint]] = defaultdict(list)
    for point in states:
        grouped[point.region_id].append(point)
    compared = agree = official_active = detected_active = 0
    regions: set[str] = set()
    with source.open("r", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            if (
                item.get("label_semantics") != "drought_hazard_event"
                or item.get("review_status") not in {"validated", "source_unit_explicit"}
                or not item.get("adm1_region_id")
            ):
                continue
            region_id = str(item["adm1_region_id"])
            target = date.fromisoformat(str(item["valid_to"]))
            candidates = [
                point for point in grouped.get(region_id, ())
                if date.fromisoformat(point.period_end) <= target
            ]
            if not candidates:
                continue
            point = max(candidates, key=lambda value: value.period_end)
            official = str(item.get("normalized_value")) in {
                "phase_alert", "phase_alarm", "phase_emergency"
            }
            compared += 1
            agree += point.active == official
            official_active += official
            detected_active += point.active and official
            regions.add(region_id)
    return {
        "status": "evaluated" if compared else "unavailable",
        "role": "external_validation_only",
        "source": "Kenya National Drought Management Authority (NDMA)",
        "comparison_count": compared,
        "region_count": len(regions),
        "agreement": agree / compared if compared else None,
        "active_recall": detected_active / official_active if official_active else None,
    }


def _condition(
    payload: Mapping[str, Any],
    soil_reference: Mapping[tuple[str, int], float],
    config: SatelliteConditionConfig,
) -> tuple[bool | None, dict[str, bool | None], dict[str, dict[str, Any]]]:
    signals = payload["signals"]
    freshness = {name: _freshness(signals.get(name)) for name in CORE_SIGNALS}
    spi = _usable_value(signals.get("spi_3m"), payload, config, "spi_3m")
    spei = _usable_value(signals.get("spei_3m"), payload, config, "spei_3m")
    met_values = [value for value in (spi, spei) if value is not None]
    meteorological = (
        None if not met_values else min(met_values) <= config.meteorological_threshold
    )
    anomaly = _usable_value(signals.get("ndvi_anomaly"), payload, config, "ndvi_anomaly")
    persistence = _usable_value(
        signals.get("ndvi_decline_persistence_dekads"),
        payload,
        config,
        "ndvi_decline_persistence_dekads",
    )
    slope = _usable_value(signals.get("ndvi_slope_3dekad"), payload, config, "ndvi_slope_3dekad")
    vegetation = (
        None
        if anomaly is None or persistence is None or slope is None
        else anomaly <= config.ndvi_anomaly_threshold
        and persistence >= config.ndvi_persistence_dekads
        and slope < 0
    )
    soil = _usable_value(
        signals.get("soil_moisture_rootzone"), payload, config, "soil_moisture_rootzone"
    )
    key = (str(payload["region_id"]), date.fromisoformat(str(payload["period_end"])).month)
    threshold = soil_reference.get(key)
    soil_stress = None if soil is None or threshold is None else soil <= threshold
    families = {
        "meteorological": meteorological,
        "vegetation": vegetation,
        "soil_moisture": soil_stress,
    }
    known = [value for value in families.values() if value is not None]
    stressed = sum(value is True for value in known)
    raw = True if stressed >= 2 else False if len(known) >= 2 else None
    return raw, families, freshness


def _soil_reference(
    payloads: Iterable[Mapping[str, Any]], config: SatelliteConditionConfig
) -> dict[tuple[str, int], float]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    cutoff = date.fromisoformat(config.reference_end)
    for payload in payloads:
        period = date.fromisoformat(str(payload["period_end"]))
        if period > cutoff:
            continue
        signal = payload["signals"].get("soil_moisture_rootzone")
        value = signal.get("value") if isinstance(signal, Mapping) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            grouped[(str(payload["region_id"]), period.month)].append(float(value))
    return {
        key: _quantile(values, config.soil_moisture_percentile)
        for key, values in grouped.items()
        if len(values) >= config.soil_reference_minimum
    }


def _usable_value(
    signal: Any,
    payload: Mapping[str, Any],
    config: SatelliteConditionConfig,
    name: str,
) -> float | None:
    if not isinstance(signal, Mapping):
        return None
    value = signal.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    available = signal.get("available_at")
    if available and _as_datetime(str(available)) > _as_datetime(str(payload["as_of"])):
        raise SatelliteContinuationError(
            f"future feature leakage: {payload['region_id']}:{payload['period_end']}:{name}"
        )
    age = signal.get("age_days")
    maximum = (config.max_signal_age_days or {}).get(name)
    if maximum is not None and (not isinstance(age, int) or age > maximum):
        return None
    return float(value)


def _features(
    payload: Mapping[str, Any],
    families: Mapping[str, bool | None],
    elapsed_days: int | None,
) -> dict[str, float | str | None]:
    result: dict[str, float | str | None] = {
        "parent_iso3": str(payload.get("parent_iso3") or "unknown"),
        "elapsed_days": float(elapsed_days or 0),
    }
    for name in CORE_SIGNALS:
        signal = payload["signals"].get(name)
        result[name] = signal.get("value") if isinstance(signal, Mapping) else None
        result[f"{name}__age_days"] = signal.get("age_days") if isinstance(signal, Mapping) else None
    for name, value in families.items():
        result[f"family_{name}_stress"] = None if value is None else float(value)
    period = date.fromisoformat(str(payload["period_end"]))
    angle = 2 * math.pi * period.timetuple().tm_yday / 365.25
    result["season_sin"] = math.sin(angle)
    result["season_cos"] = math.cos(angle)
    return result


def _fit_baselines(
    rows: Sequence[SatelliteSample], config: SatelliteConditionConfig
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for horizon in config.horizons_days:
        known = [row for row in rows if row.targets.get(horizon) is not None]
        if not known:
            raise SatelliteContinuationError(f"no historical support for {horizon}-day baseline")
        global_success = sum(int(cast(int, row.targets[horizon])) for row in known)
        bins: dict[str, dict[str, Any]] = {}
        grouped: dict[int, list[SatelliteSample]] = defaultdict(list)
        for row in known:
            grouped[row.elapsed_days // config.elapsed_bin_days].append(row)
        for elapsed_bin, values in sorted(grouped.items()):
            success = sum(int(cast(int, row.targets[horizon])) for row in values)
            bins[str(elapsed_bin)] = {
                "probability": (success + 1) / (len(values) + 2),
                "known_count": len(values),
                "episode_count": len({row.episode_id for row in values}),
            }
        result[str(horizon)] = {
            "global": {
                "probability": (global_success + 1) / (len(known) + 2),
                "known_count": len(known),
                "episode_count": len({row.episode_id for row in known}),
            },
            "elapsed_bins": bins,
        }
    return result


def _walk_forward_validation(
    rows: Sequence[SatelliteSample], config: SatelliteConditionConfig
) -> dict[str, Any]:
    predictions: list[tuple[str, int, float, float]] = []
    folds: list[dict[str, Any]] = []
    for year in (2022, 2023):
        cutoff = date(year, 1, 1)
        next_cutoff = date(year + 1, 1, 1)
        horizon = config.ml_horizon_days
        train = [
            row for row in rows
            if row.targets.get(horizon) is not None
            and date.fromisoformat(row.period_end) + timedelta(days=horizon) < cutoff
        ]
        train_episodes = {row.episode_id for row in train}
        test = [
            row for row in rows
            if row.targets.get(horizon) is not None
            and cutoff <= date.fromisoformat(row.period_end)
            and date.fromisoformat(row.period_end) + timedelta(days=horizon) < next_cutoff
            and row.episode_id not in train_episodes
        ]
        if not train or not test or {
            int(cast(int, row.targets[horizon])) for row in train
        } != {0, 1}:
            continue
        estimator = _fit_estimator(train, config)
        baseline = _fit_baselines(train, config)[str(horizon)]
        ml_values = estimator.predict_proba([row.features for row in test])[:, 1]
        baseline_values = [_baseline_lookup(baseline, row.elapsed_days, config)[0] for row in test]
        actual = [int(cast(int, row.targets[horizon])) for row in test]
        fold_predictions = [
            (row.episode_id, target, float(ml), float(base))
            for row, target, ml, base in zip(test, actual, ml_values, baseline_values, strict=True)
        ]
        ml_brier = _episode_weighted_brier(fold_predictions, probability_index=2)
        baseline_brier = _episode_weighted_brier(fold_predictions, probability_index=3)
        folds.append({
            "year": year,
            "train_rows": len(train),
            "test_rows": len(test),
            "test_episodes": len({row.episode_id for row in test}),
            "ml_brier": ml_brier,
            "baseline_brier": baseline_brier,
            "brier_skill_score": 1 - ml_brier / baseline_brier if baseline_brier else None,
        })
        predictions.extend(fold_predictions)
    if not predictions:
        return {
            "status": "inconclusive",
            "reason_codes": ["walk_forward_support_insufficient"],
            "folds": folds,
            "test_rows": 0,
        }
    actual = [item[1] for item in predictions]
    ml_values = [item[2] for item in predictions]
    baseline_values = [item[3] for item in predictions]
    ml_brier = _episode_weighted_brier(predictions, probability_index=2)
    baseline_brier = _episode_weighted_brier(predictions, probability_index=3)
    bss = 1 - ml_brier / baseline_brier if baseline_brier else -math.inf
    ece = _ece(actual, ml_values)
    lower, upper = _episode_bootstrap_delta(predictions, config.seed)
    improved = sum(fold["ml_brier"] < fold["baseline_brier"] for fold in folds)
    qualified = (
        len(predictions) >= config.ml_min_backtest_rows
        and bss > 0
        and ece <= config.ml_max_ece
        and improved >= max(1, len(folds) // 2)
    )
    return {
        "status": "inconclusive",
        "qualified_for_experimental_serving": qualified,
        "test_rows": len(predictions),
        "test_episodes": len({item[0] for item in predictions}),
        "episode_weighted_brier": ml_brier,
        "episode_weighted_brier_skill_score": bss,
        "episode_weighted_ece": ece,
        "bootstrap_delta_brier_ci95": [lower, upper],
        "improved_outer_folds": improved,
        "outer_fold_count": len(folds),
        "folds": folds,
        "reason_codes": [] if qualified else ["satellite_ml_gate_not_met"],
    }


def _fit_estimator(
    rows: Sequence[SatelliteSample], config: SatelliteConditionConfig
) -> Pipeline:
    estimator = Pipeline([
        ("vectorize", DictVectorizer(sparse=False)),
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=1000, random_state=config.seed)),
    ])
    estimator.fit(
        [row.features for row in rows],
        [int(cast(int, row.targets[config.ml_horizon_days])) for row in rows],
    )
    return estimator


def _baseline_probabilities(
    bundle: SatelliteServingBundle, point: SatelliteStatePoint
) -> dict[int, float]:
    config = config_from_mapping(bundle.config)
    values: dict[int, float] = {}
    prior = 1.0
    for horizon in config.horizons_days:
        baseline = bundle.baselines[str(horizon)]
        probability, _quality = _baseline_lookup(baseline, point.elapsed_days or 0, config)
        prior = min(prior, probability)
        values[horizon] = prior
    return values


def _baseline_lookup(
    baseline: Mapping[str, Any], elapsed_days: int, config: SatelliteConditionConfig
) -> tuple[float, dict[str, Any]]:
    elapsed_bin = str(elapsed_days // config.elapsed_bin_days)
    value = baseline.get("elapsed_bins", {}).get(elapsed_bin)
    if not isinstance(value, Mapping) or int(value.get("known_count", 0)) < 5:
        value = baseline["global"]
        scope = "global"
    else:
        scope = "elapsed_bin"
    return float(value["probability"]), {
        "status": "ok",
        "scope": scope,
        "known_count": int(value["known_count"]),
        "episode_count": int(value["episode_count"]),
    }


def _ml_estimate(bundle: SatelliteServingBundle, point: SatelliteStatePoint) -> dict[str, Any]:
    validation = bundle.validation
    qualified = bool(validation.get("qualified_for_experimental_serving"))
    reasons: list[str] = []
    if bundle.estimator is None:
        reasons.append("satellite_ml_artifact_unavailable")
    if not qualified:
        reasons.extend(str(value) for value in validation.get("reason_codes", ()))
    outside = _out_of_range_fraction(bundle.numeric_ranges, point.features)
    if outside > 0.5:
        reasons.append("feature_drift_above_limit")
    base = {
        "kind": "experimental_ml_prediction",
        "status": "unavailable" if reasons else "available",
        "probability": None,
        "estimator_kind": "ml",
        "model": "satellite_logistic_continuation_30d",
        "experimental": True,
        "operational_use": False,
        "validation": validation,
        "quality": {"status": "blocked" if reasons else "ok", "out_of_range_fraction": outside},
        "reason_codes": sorted(set(reasons)),
        "drivers": [],
        "artifact": {
            "schema_version": bundle.schema_version,
            "run_hash": bundle.run_hash,
            "trained_through": bundle.trained_through,
        },
    }
    if reasons or bundle.estimator is None:
        return base
    probability = float(bundle.estimator.predict_proba([point.features])[0, 1])
    return base | {
        "probability": probability,
        "drivers": _drivers(bundle.estimator, point.features),
    }


def _baseline_estimate(
    bundle: SatelliteServingBundle,
    point: SatelliteStatePoint,
    horizon: int,
    probability: float,
) -> dict[str, Any]:
    config = config_from_mapping(bundle.config)
    _raw, quality = _baseline_lookup(
        bundle.baselines[str(horizon)], point.elapsed_days or 0, config
    )
    return {
        "kind": "historical_reference",
        "status": "available",
        "probability": probability,
        "estimator_kind": "baseline",
        "model": "satellite_episode_survival",
        "experimental": False,
        "operational_use": False,
        "validation": {"status": "historical_reference", "target": TARGET},
        "quality": quality,
        "reason_codes": [],
        "drivers": [],
        "evidence": {
            "condition_basis": "satellite_multisignal",
            "state_version": STATE_VERSION,
            "elapsed_days": point.elapsed_days,
            "causal": False,
        },
    }


def _active_item(
    point: SatelliteStatePoint, horizon: int, estimates: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "region_id": point.region_id,
        "as_of": point.period_end,
        "horizon_days": horizon,
        "target": TARGET,
        "current_drought_status": "active",
        "current_phase": "satellite_condition_active",
        "current_trend": point.trend,
        "elapsed_days": point.elapsed_days,
        "status": "available",
        "reason_codes": [],
        "estimates": estimates,
        "condition_basis": "satellite_multisignal",
        "state_version": STATE_VERSION,
        "signal_freshness": point.signal_freshness,
    }


def _inactive_item(point: SatelliteStatePoint, horizon: int) -> dict[str, Any]:
    return {
        "region_id": point.region_id,
        "as_of": point.period_end,
        "horizon_days": horizon,
        "target": TARGET,
        "current_drought_status": "inactive",
        "current_phase": "satellite_condition_inactive",
        "current_trend": point.trend,
        "elapsed_days": None,
        "status": "not_applicable",
        "reason_codes": ["no_active_satellite_drought_condition"],
        "estimates": [],
        "condition_basis": "satellite_multisignal",
        "state_version": STATE_VERSION,
        "signal_freshness": point.signal_freshness,
    }


def _latest_states(states: Iterable[SatelliteStatePoint]) -> dict[str, SatelliteStatePoint]:
    result: dict[str, SatelliteStatePoint] = {}
    for point in states:
        current = result.get(point.region_id)
        if current is None or point.period_end > current.period_end:
            result[point.region_id] = point
    return result


def _freshness(signal: Any) -> dict[str, Any]:
    if not isinstance(signal, Mapping):
        return {"quality": "missing", "observed_at": None, "available_at": None, "age_days": None}
    return {
        "quality": signal.get("quality"),
        "observed_at": signal.get("observed_at"),
        "available_at": signal.get("available_at"),
        "age_days": signal.get("age_days"),
        "source_collection": signal.get("source_collection"),
        "source_version": signal.get("source_version"),
        "missing_reason": signal.get("missing_reason"),
    }


def _trend(raw: bool | None, previous: bool | None, active: bool) -> str:
    if raw is None:
        return "unknown"
    if raw and previous is not True:
        return "deteriorating"
    if not raw and active:
        return "improving"
    return "persistent" if active else "stable"


def _episode_id(region_id: str, start: str) -> str:
    return f"sat-episode:{hashlib.sha256(f'{region_id}:{start}:{STATE_VERSION}'.encode()).hexdigest()[:20]}"


def _drivers(estimator: Pipeline, features: Mapping[str, Any]) -> list[dict[str, Any]]:
    vectorizer = estimator.named_steps["vectorize"]
    imputer = estimator.named_steps["impute"]
    scaler = estimator.named_steps["scale"]
    model = estimator.named_steps["model"]
    names = vectorizer.get_feature_names_out()
    vectorized = vectorizer.transform([dict(features)])
    imputed = imputer.transform(vectorized)
    names = imputer.get_feature_names_out(names)
    scaled = scaler.transform(imputed)
    values = sorted(
        (
            (str(name), float(value) * float(coefficient))
            for name, value, coefficient in zip(names, scaled[0], model.coef_[0], strict=True)
        ),
        key=lambda item: (-abs(item[1]), item[0]),
    )[:3]
    return [
        {
            "feature": name.replace("missingindicator_", "missing:")[:120],
            "direction": (
                "higher_continuation_probability" if contribution >= 0
                else "lower_continuation_probability"
            ),
            "contribution": round(contribution, 6),
            "method": "logistic_logit_contribution",
            "causal": False,
            "statement": "Association in the experimental model; not a causal effect.",
        }
        for name, contribution in values
    ]


def _numeric_ranges(rows: Sequence[SatelliteSample]) -> dict[str, tuple[float, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for name, value in row.features.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                values[name].append(float(value))
    return {name: (min(items), max(items)) for name, items in sorted(values.items()) if items}


def _out_of_range_fraction(
    ranges: Mapping[str, tuple[float, float]], features: Mapping[str, Any]
) -> float:
    comparable = outside = 0
    for name, value in features.items():
        if name not in ranges or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        comparable += 1
        outside += not ranges[name][0] <= float(value) <= ranges[name][1]
    return outside / comparable if comparable else 1.0


def _episode_bootstrap_delta(
    predictions: Sequence[tuple[str, int, float, float]], seed: int
) -> tuple[float, float]:
    grouped: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for episode, target_value, ml, baseline in predictions:
        grouped[episode].append((target_value, ml, baseline))
    episode_ids = sorted(grouped)
    if len(episode_ids) < 2:
        return 0.0, 0.0
    rng = random.Random(seed)
    deltas = []
    for _ in range(500):
        sampled = [rng.choice(episode_ids) for _ in episode_ids]
        episode_deltas = []
        for episode in sampled:
            rows = grouped[episode]
            outcomes = [item[0] for item in rows]
            episode_deltas.append(
                _brier(outcomes, [item[1] for item in rows])
                - _brier(outcomes, [item[2] for item in rows])
            )
        deltas.append(sum(episode_deltas) / len(episode_deltas))
    deltas.sort()
    return deltas[int(0.025 * len(deltas))], deltas[min(len(deltas) - 1, int(0.975 * len(deltas)))]


def _episode_weighted_brier(
    predictions: Sequence[tuple[str, int, float, float]], *, probability_index: int
) -> float:
    grouped: dict[str, list[float]] = defaultdict(list)
    for item in predictions:
        grouped[item[0]].append((float(item[probability_index]) - int(item[1])) ** 2)
    return sum(sum(values) / len(values) for values in grouped.values()) / len(grouped)


def _brier(actual: Sequence[int], probabilities: Sequence[float]) -> float:
    return sum((float(p) - int(y)) ** 2 for y, p in zip(actual, probabilities, strict=True)) / len(actual)


def _ece(actual: Sequence[int], probabilities: Sequence[float]) -> float:
    total = len(actual)
    value = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        members = [
            (y, p) for y, p in zip(actual, probabilities, strict=True)
            if lower <= p < lower + 0.2 or (lower == 0.8 and p == 1.0)
        ]
        if members:
            value += len(members) / total * abs(
                sum(p for _, p in members) / len(members)
                - sum(y for y, _ in members) / len(members)
            )
    return value


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def _as_datetime(value: str) -> datetime:
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


__all__ = [
    "SatelliteConditionConfig",
    "SatelliteContinuationError",
    "SatelliteServingBundle",
    "SatelliteStatePoint",
    "TARGET",
    "build_satellite_samples",
    "config_from_mapping",
    "derive_satellite_states",
    "freeze_satellite_bundle",
    "load_feature_payloads",
    "materialize_satellite_snapshot",
    "validate_against_ndma",
]

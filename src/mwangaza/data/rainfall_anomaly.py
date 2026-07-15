from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from mwangaza.contracts import Anomaly, Baseline, IndicatorObservation
from mwangaza.data.rainfall_climatology import RainfallClimatologyBaseline


class RainfallAnomalyError(ValueError):
    pass


@dataclass(frozen=True)
class RainfallAnomalyConfig:
    percent_epsilon: float = 1e-6
    min_percentile_observations: int = 3
    deficit_threshold_percent: float = -20.0
    excess_threshold_percent: float = 20.0


def compute_rainfall_anomaly(
    current: IndicatorObservation,
    baseline: Baseline | RainfallClimatologyBaseline,
    *,
    config: RainfallAnomalyConfig | None = None,
) -> Anomaly:
    resolved_config = config or RainfallAnomalyConfig()
    _validate_config(resolved_config)
    baseline_payload = baseline.baseline if isinstance(baseline, RainfallClimatologyBaseline) else baseline
    historical_values = _historical_values(baseline)
    _validate_inputs(current, baseline_payload)

    quality_flag = _most_restrictive_quality(current.quality_flag, baseline_payload.quality_flag)
    baseline_id = _baseline_id(baseline_payload)
    metadata: dict[str, object] = {
        "current_id": _current_id(current),
        "baseline_id": baseline_id,
        "current_value": current.value,
        "baseline_mean": baseline_payload.mean,
        "absolute_anomaly": None,
        "percent_anomaly": None,
        "empirical_percentile": None,
        "classification": "not_conclusive",
        "percent_epsilon": resolved_config.percent_epsilon,
        "min_percentile_observations": resolved_config.min_percentile_observations,
        "deficit_threshold_percent": resolved_config.deficit_threshold_percent,
        "excess_threshold_percent": resolved_config.excess_threshold_percent,
    }

    if current.value is None:
        metadata["non_conclusive_reason"] = "current_no_data"
        return _result(current, baseline_id, quality_flag, None, metadata)
    if baseline_payload.mean is None:
        metadata["non_conclusive_reason"] = "baseline_insufficient_history"
        return _result(current, baseline_id, quality_flag, None, metadata)

    _validate_rainfall_value("current.value", current.value)
    _validate_rainfall_value("baseline.mean", baseline_payload.mean)
    absolute = current.value - baseline_payload.mean
    metadata["absolute_anomaly"] = absolute

    percent = None
    if abs(baseline_payload.mean) > resolved_config.percent_epsilon:
        percent = (absolute / baseline_payload.mean) * 100.0
        metadata["percent_anomaly"] = percent
        metadata["classification"] = _classification(percent, resolved_config)
    else:
        metadata["percent_anomaly_reason"] = "baseline_mean_within_epsilon"

    if len(historical_values) >= resolved_config.min_percentile_observations:
        metadata["empirical_percentile"] = _empirical_percentile(current.value, historical_values)
    else:
        metadata["empirical_percentile_reason"] = "insufficient_observations"

    value = absolute if quality_flag in {"ok", "degraded"} else None
    if value is None:
        metadata["non_conclusive_reason"] = f"quality_{quality_flag}"
        metadata["classification"] = "not_conclusive"
    return _result(current, baseline_id, quality_flag, value, metadata)


def _validate_config(config: RainfallAnomalyConfig) -> None:
    if config.percent_epsilon <= 0 or not math.isfinite(config.percent_epsilon):
        raise RainfallAnomalyError("percent_epsilon must be positive and finite")
    if config.min_percentile_observations <= 0:
        raise RainfallAnomalyError("min_percentile_observations must be positive")
    if not math.isfinite(config.deficit_threshold_percent) or not math.isfinite(config.excess_threshold_percent):
        raise RainfallAnomalyError("classification thresholds must be finite")
    if config.deficit_threshold_percent >= config.excess_threshold_percent:
        raise RainfallAnomalyError("deficit threshold must be below excess threshold")


def _validate_inputs(current: IndicatorObservation, baseline: Baseline) -> None:
    if current.indicator != "rainfall_mm" or baseline.indicator != "rainfall_mm":
        raise RainfallAnomalyError("rainfall anomaly requires rainfall_mm indicator inputs")
    if current.unit != "mm" or baseline.unit != "mm":
        raise RainfallAnomalyError("rainfall anomaly requires mm units")
    if current.region_id != baseline.region_id:
        raise RainfallAnomalyError("current and baseline region_id must match")


def _validate_rainfall_value(field_name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise RainfallAnomalyError(f"{field_name} must be non-negative and finite")


def _most_restrictive_quality(current_flag: str, baseline_flag: str) -> str:
    rank = {
        "ok": 0,
        "degraded": 1,
        "insufficient_history": 2,
        "no_data": 3,
        "invalid": 4,
    }
    if current_flag not in rank or baseline_flag not in rank:
        raise RainfallAnomalyError("unsupported quality_flag")
    return max((current_flag, baseline_flag), key=lambda flag: rank[flag])


def _historical_values(baseline: Baseline | RainfallClimatologyBaseline) -> list[float]:
    if isinstance(baseline, RainfallClimatologyBaseline):
        included_years = set(baseline.included_years)
        values = [
            item.accumulated_mm
            for item in baseline.yearly_observations
            if item.year in included_years and item.quality_flag == "ok"
        ]
    else:
        raw = baseline.metadata.get("historical_values") or baseline.metadata.get("included_values")
        values = raw if isinstance(raw, list) else []
    parsed: list[float] = []
    for value in values:
        if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise RainfallAnomalyError("historical rainfall values must be non-negative and finite")
        parsed.append(float(value))
    return parsed


def _empirical_percentile(current_value: float, historical_values: list[float]) -> float:
    if not historical_values:
        raise RainfallAnomalyError("empirical percentile requires historical values")
    below_or_equal = sum(1 for value in historical_values if value <= current_value)
    percentile = (below_or_equal / len(historical_values)) * 100.0
    return min(100.0, max(0.0, percentile))


def _classification(percent_anomaly: float, config: RainfallAnomalyConfig) -> str:
    if percent_anomaly <= config.deficit_threshold_percent:
        return "deficit"
    if percent_anomaly >= config.excess_threshold_percent:
        return "excess"
    return "normal"


def _current_id(current: IndicatorObservation) -> str:
    candidate = current.metadata.get("current_id") or current.metadata.get("observation_id") or current.metadata.get("id")
    if isinstance(candidate, str) and candidate:
        return candidate
    return "|".join([current.region_id, current.indicator, current.period_start, current.period_end, current.source])


def _baseline_id(baseline: Baseline) -> str:
    candidate = baseline.metadata.get("baseline_id") or baseline.metadata.get("baseline_version") or baseline.metadata.get("id")
    if isinstance(candidate, str) and candidate:
        return candidate
    return "|".join(
        [
            baseline.region_id,
            baseline.indicator,
            str(baseline.baseline_start_year),
            str(baseline.baseline_end_year),
            baseline.source,
        ]
    )


def _result(
    current: IndicatorObservation,
    baseline_id: str,
    quality_flag: str,
    value: float | None,
    metadata: dict[str, object],
) -> Anomaly:
    anomaly = Anomaly(
        region_id=current.region_id,
        indicator="rainfall_mm",
        period_start=current.period_start,
        period_end=current.period_end,
        value=value,
        unit="mm",
        baseline_id=baseline_id,
        method="current_minus_mean",
        source="mwangaza.anomaly.rainfall",
        quality_flag=quality_flag,
        is_simulated=current.is_simulated,
        metadata=metadata,
    )
    anomaly.validate()
    return anomaly

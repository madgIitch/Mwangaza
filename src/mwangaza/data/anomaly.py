from __future__ import annotations

import math
from dataclasses import dataclass

from mwangaza.contracts import Anomaly, Baseline, IndicatorObservation


class NdviAnomalyError(ValueError):
    pass


@dataclass(frozen=True)
class NdviAnomalyConfig:
    percent_epsilon: float = 1e-6
    zscore_epsilon: float = 1e-6


def compute_ndvi_anomaly(
    current: IndicatorObservation,
    baseline: Baseline,
    *,
    config: NdviAnomalyConfig | None = None,
) -> Anomaly:
    resolved_config = config or NdviAnomalyConfig()
    _validate_config(resolved_config)
    _validate_inputs(current, baseline)

    quality_flag = _most_restrictive_quality(current.quality_flag, baseline.quality_flag)
    current_id = _current_id(current)
    baseline_id = _baseline_id(baseline)
    metadata: dict[str, object] = {
        "current_id": current_id,
        "baseline_id": baseline_id,
        "epsilon": resolved_config.percent_epsilon,
        "percent_epsilon": resolved_config.percent_epsilon,
        "zscore_epsilon": resolved_config.zscore_epsilon,
        "baseline_mean": baseline.mean,
        "baseline_stddev": baseline.stddev,
        "current_value": current.value,
        "absolute_anomaly": None,
        "percent_anomaly": None,
        "z_score": None,
    }

    if current.value is None:
        metadata["non_conclusive_reason"] = "current_no_data"
        return _result(current, baseline_id, quality_flag, None, metadata)
    if baseline.mean is None:
        metadata["non_conclusive_reason"] = "baseline_insufficient_history"
        return _result(current, baseline_id, quality_flag, None, metadata)

    _validate_ndvi_value("current.value", current.value)
    _validate_ndvi_value("baseline.mean", baseline.mean)
    absolute = current.value - baseline.mean
    metadata["absolute_anomaly"] = absolute

    if abs(baseline.mean) > resolved_config.percent_epsilon:
        metadata["percent_anomaly"] = (absolute / baseline.mean) * 100.0
    else:
        metadata["percent_anomaly_reason"] = "baseline_mean_within_epsilon"

    if baseline.stddev is not None:
        if not math.isfinite(baseline.stddev) or baseline.stddev < 0:
            raise NdviAnomalyError("baseline.stddev must be non-negative and finite")
        if baseline.stddev > resolved_config.zscore_epsilon:
            metadata["z_score"] = absolute / baseline.stddev
        else:
            metadata["z_score_reason"] = "baseline_stddev_within_epsilon"
    else:
        metadata["z_score_reason"] = "baseline_stddev_missing"

    value = absolute if quality_flag in {"ok", "degraded"} else None
    return _result(current, baseline_id, quality_flag, value, metadata)


def _validate_config(config: NdviAnomalyConfig) -> None:
    if config.percent_epsilon <= 0 or not math.isfinite(config.percent_epsilon):
        raise NdviAnomalyError("percent_epsilon must be positive and finite")
    if config.zscore_epsilon <= 0 or not math.isfinite(config.zscore_epsilon):
        raise NdviAnomalyError("zscore_epsilon must be positive and finite")


def _validate_inputs(current: IndicatorObservation, baseline: Baseline) -> None:
    if current.indicator != "ndvi" or baseline.indicator != "ndvi":
        raise NdviAnomalyError("NDVI anomaly requires ndvi indicator inputs")
    if current.unit != "index" or baseline.unit != "index":
        raise NdviAnomalyError("NDVI anomaly requires index units")
    if current.region_id != baseline.region_id:
        raise NdviAnomalyError("current and baseline region_id must match")


def _validate_ndvi_value(field_name: str, value: float) -> None:
    if not math.isfinite(value) or not -1.0 <= value <= 1.0:
        raise NdviAnomalyError(f"{field_name} must be finite and inside [-1.0, 1.0]")


def _most_restrictive_quality(current_flag: str, baseline_flag: str) -> str:
    rank = {
        "ok": 0,
        "degraded": 1,
        "insufficient_history": 2,
        "no_data": 3,
        "invalid": 4,
    }
    if current_flag not in rank or baseline_flag not in rank:
        raise NdviAnomalyError("unsupported quality_flag")
    return max((current_flag, baseline_flag), key=lambda flag: rank[flag])


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
        indicator="ndvi",
        period_start=current.period_start,
        period_end=current.period_end,
        value=value,
        unit="index",
        baseline_id=baseline_id,
        method="current_minus_mean",
        source="mwangaza.anomaly.ndvi",
        quality_flag=quality_flag,
        is_simulated=current.is_simulated,
        metadata=metadata,
    )
    anomaly.validate()
    return anomaly

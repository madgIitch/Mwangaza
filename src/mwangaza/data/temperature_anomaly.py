from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from mwangaza.contracts import Anomaly, Baseline, IndicatorObservation
from mwangaza.data.lst import DEFAULT_LST_COLLECTION
from mwangaza.regions import get_region


class TemperatureAnomalyError(ValueError):
    pass


@dataclass(frozen=True)
class LstClimatologyConfig:
    start_year: int
    end_year: int
    min_years: int = 10
    collection_id: str = DEFAULT_LST_COLLECTION
    product_variant: str = "day"
    min_valid_celsius: float = -90.0
    max_valid_celsius: float = 80.0


@dataclass(frozen=True)
class LstYearObservation:
    year: int
    mean_c: float | None
    median_c: float | None = None
    quality_flag: str = "ok"
    source: str | None = None
    metadata: dict[str, Any] | None = None


class LstClimatologyAdapter(Protocol):
    def query_lst_year(
        self,
        geometry: dict[str, Any],
        year: int,
        season_start: str,
        season_end: str,
        config: LstClimatologyConfig,
    ) -> LstYearObservation:
        ...


@dataclass(frozen=True)
class TemperatureAnomalyConfig:
    zscore_epsilon: float = 1e-6
    allow_variant_mismatch: bool = False
    min_valid_celsius: float = -90.0
    max_valid_celsius: float = 80.0


def compute_lst_climatology(
    region_id: str,
    season_start: str,
    season_end: str,
    current_period_start: str,
    current_period_end: str,
    *,
    adapter: LstClimatologyAdapter,
    config: LstClimatologyConfig,
) -> Baseline:
    _validate_climatology_config(config)
    current_start = _parse_datetime(current_period_start, "current_period_start")
    current_end = _parse_datetime(current_period_end, "current_period_end")
    if current_start > current_end:
        raise TemperatureAnomalyError("current period is inverted")
    start_month, start_day = _parse_month_day(season_start, "season_start")
    end_month, end_day = _parse_month_day(season_end, "season_end")

    region = get_region(region_id)
    included_years: list[int] = []
    excluded_years: list[int] = []
    values: list[float] = []

    for year in range(config.start_year, config.end_year + 1):
        _season_dates_for_year(year, start_month, start_day, end_month, end_day)
        observation = adapter.query_lst_year(region.geometry, year, season_start, season_end, config)
        if observation.year != year:
            raise TemperatureAnomalyError("adapter returned observation for the wrong year")
        if observation.quality_flag != "ok" or observation.mean_c is None:
            excluded_years.append(year)
            continue
        _validate_temperature_value("mean_c", observation.mean_c, config.min_valid_celsius, config.max_valid_celsius)
        included_years.append(year)
        values.append(float(observation.mean_c))

    metadata = _baseline_metadata(
        region_id=region.id,
        config=config,
        season_start=season_start,
        season_end=season_end,
        included_years=included_years,
        excluded_years=excluded_years,
    )
    period_start, period_end = _baseline_period(config, start_month, start_day, end_month, end_day)

    if len(values) < config.min_years:
        baseline = Baseline(
            region_id=region.id,
            indicator="lst_c",
            period_start=period_start,
            period_end=period_end,
            baseline_start_year=config.start_year,
            baseline_end_year=config.end_year,
            mean=None,
            median=None,
            stddev=None,
            observations=len(values),
            unit="celsius",
            source=config.collection_id,
            quality_flag="insufficient_history",
            is_simulated=False,
            metadata=metadata,
        )
        baseline.validate()
        return baseline

    baseline = Baseline(
        region_id=region.id,
        indicator="lst_c",
        period_start=period_start,
        period_end=period_end,
        baseline_start_year=config.start_year,
        baseline_end_year=config.end_year,
        mean=statistics.fmean(values),
        median=statistics.median(values),
        stddev=statistics.pstdev(values) if len(values) >= 2 else None,
        observations=len(values),
        unit="celsius",
        source=config.collection_id,
        quality_flag="ok",
        is_simulated=False,
        metadata=metadata,
    )
    baseline.validate()
    return baseline


def compute_temperature_anomaly(
    current: IndicatorObservation,
    baseline: Baseline,
    *,
    config: TemperatureAnomalyConfig | None = None,
) -> Anomaly:
    resolved_config = config or TemperatureAnomalyConfig()
    _validate_anomaly_config(resolved_config)
    _validate_inputs(current, baseline, resolved_config)

    quality_flag = _most_restrictive_quality(current.quality_flag, baseline.quality_flag)
    baseline_id = _baseline_id(baseline)
    product_variant = _product_variant(current.metadata, fallback=_product_variant(baseline.metadata))
    metadata: dict[str, object] = {
        "current_id": _current_id(current),
        "baseline_id": baseline_id,
        "baseline_version": baseline.metadata.get("baseline_version"),
        "product_variant": product_variant,
        "current_value": current.value,
        "baseline_mean": baseline.mean,
        "baseline_stddev": baseline.stddev,
        "absolute_anomaly_c": None,
        "z_score": None,
        "zscore_epsilon": resolved_config.zscore_epsilon,
    }

    if current.value is None:
        metadata["non_conclusive_reason"] = "current_no_data"
        return _result(current, baseline_id, quality_flag, None, metadata)
    if baseline.mean is None:
        metadata["non_conclusive_reason"] = "baseline_insufficient_history"
        return _result(current, baseline_id, quality_flag, None, metadata)

    _validate_temperature_value(
        "current.value",
        current.value,
        resolved_config.min_valid_celsius,
        resolved_config.max_valid_celsius,
    )
    _validate_temperature_value(
        "baseline.mean",
        baseline.mean,
        resolved_config.min_valid_celsius,
        resolved_config.max_valid_celsius,
    )
    absolute = current.value - baseline.mean
    metadata["absolute_anomaly_c"] = absolute

    if baseline.stddev is not None:
        if not math.isfinite(baseline.stddev) or baseline.stddev < 0:
            raise TemperatureAnomalyError("baseline.stddev must be non-negative and finite")
        if baseline.stddev > resolved_config.zscore_epsilon:
            metadata["z_score"] = absolute / baseline.stddev
        else:
            metadata["z_score_reason"] = "baseline_stddev_within_epsilon"
    else:
        metadata["z_score_reason"] = "baseline_stddev_missing"

    value = absolute if quality_flag in {"ok", "degraded"} else None
    if value is None:
        metadata["non_conclusive_reason"] = f"quality_{quality_flag}"
    return _result(current, baseline_id, quality_flag, value, metadata)


def _validate_climatology_config(config: LstClimatologyConfig) -> None:
    if config.start_year > config.end_year:
        raise TemperatureAnomalyError("climatology year window is inverted")
    if config.min_years <= 0:
        raise TemperatureAnomalyError("min_years must be positive")
    if not config.collection_id:
        raise TemperatureAnomalyError("collection_id is required")
    _validate_product_variant(config.product_variant)
    if config.min_valid_celsius >= config.max_valid_celsius:
        raise TemperatureAnomalyError("physical temperature range is inverted")


def _validate_anomaly_config(config: TemperatureAnomalyConfig) -> None:
    if config.zscore_epsilon <= 0 or not math.isfinite(config.zscore_epsilon):
        raise TemperatureAnomalyError("zscore_epsilon must be positive and finite")
    if config.min_valid_celsius >= config.max_valid_celsius:
        raise TemperatureAnomalyError("physical temperature range is inverted")


def _validate_inputs(
    current: IndicatorObservation,
    baseline: Baseline,
    config: TemperatureAnomalyConfig,
) -> None:
    if current.indicator != "lst_c" or baseline.indicator != "lst_c":
        raise TemperatureAnomalyError("temperature anomaly requires lst_c indicator inputs")
    if current.unit != "celsius" or baseline.unit != "celsius":
        raise TemperatureAnomalyError("temperature anomaly requires celsius units")
    if current.region_id != baseline.region_id:
        raise TemperatureAnomalyError("current and baseline region_id must match")
    current_variant = _product_variant(current.metadata)
    baseline_variant = _product_variant(baseline.metadata)
    _validate_product_variant(current_variant)
    _validate_product_variant(baseline_variant)
    if current_variant != baseline_variant and not config.allow_variant_mismatch:
        raise TemperatureAnomalyError("current and baseline product_variant must match")


def _validate_temperature_value(field_name: str, value: float, min_valid: float, max_valid: float) -> None:
    if not math.isfinite(value):
        raise TemperatureAnomalyError(f"{field_name} must be finite")
    if value < min_valid or value > max_valid:
        raise TemperatureAnomalyError(f"{field_name} is outside the physical temperature range")


def _validate_product_variant(product_variant: str) -> None:
    if product_variant not in {"day", "night"}:
        raise TemperatureAnomalyError("product_variant must be day or night")


def _product_variant(metadata: dict[str, Any], fallback: str | None = None) -> str:
    value = metadata.get("product_variant", fallback)
    return value if isinstance(value, str) else ""


def _most_restrictive_quality(current_flag: str, baseline_flag: str) -> str:
    rank = {
        "ok": 0,
        "degraded": 1,
        "insufficient_history": 2,
        "no_data": 3,
        "invalid": 4,
    }
    if current_flag not in rank or baseline_flag not in rank:
        raise TemperatureAnomalyError("unsupported quality_flag")
    return max((current_flag, baseline_flag), key=lambda flag: rank[flag])


def _parse_month_day(value: str, field_name: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise TemperatureAnomalyError(f"{field_name} must use MM-DD format")
    try:
        month, day = int(parts[0]), int(parts[1])
        date(2001, month, day)
    except ValueError as exc:
        raise TemperatureAnomalyError(f"{field_name} is not a valid month-day") from exc
    return month, day


def _season_dates_for_year(
    year: int,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
) -> tuple[date, date]:
    try:
        start = date(year, start_month, start_day)
        end_year = year + 1 if (end_month, end_day) < (start_month, start_day) else year
        end = date(end_year, end_month, end_day)
    except ValueError as exc:
        raise TemperatureAnomalyError("season day is invalid for a climatology year") from exc
    if start > end:
        raise TemperatureAnomalyError("season window is inverted")
    return start, end


def _baseline_period(
    config: LstClimatologyConfig,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
) -> tuple[str, str]:
    start, _ = _season_dates_for_year(config.start_year, start_month, start_day, end_month, end_day)
    _, end = _season_dates_for_year(config.end_year, start_month, start_day, end_month, end_day)
    return f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T00:00:00Z"


def _baseline_metadata(
    *,
    region_id: str,
    config: LstClimatologyConfig,
    season_start: str,
    season_end: str,
    included_years: list[int],
    excluded_years: list[int],
) -> dict[str, Any]:
    version_input = "|".join(
        [
            region_id,
            "lst_c",
            str(config.start_year),
            str(config.end_year),
            season_start,
            season_end,
            config.collection_id,
            config.product_variant,
            ",".join(str(year) for year in included_years),
        ]
    )
    return {
        "baseline_version": hashlib.sha256(version_input.encode("utf-8")).hexdigest()[:16],
        "collection_id": config.collection_id,
        "product_variant": config.product_variant,
        "season_start": season_start,
        "season_end": season_end,
        "included_years": list(included_years),
        "excluded_years": list(excluded_years),
        "min_years": config.min_years,
    }


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemperatureAnomalyError(f"{field_name} must be ISO8601") from exc


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
        indicator="lst_c",
        period_start=current.period_start,
        period_end=current.period_end,
        value=value,
        unit="celsius",
        baseline_id=baseline_id,
        method="current_minus_mean",
        source="mwangaza.anomaly.temperature",
        quality_flag=quality_flag,
        is_simulated=current.is_simulated,
        metadata=metadata,
    )
    anomaly.validate()
    return anomaly

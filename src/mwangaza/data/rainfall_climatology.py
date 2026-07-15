from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from mwangaza.contracts import Baseline
from mwangaza.data.rainfall import (
    RainfallAdapter,
    RainfallCollectionConfig,
    RainfallQueryResult,
)
from mwangaza.regions import get_region


class RainfallClimatologyError(ValueError):
    pass


@dataclass(frozen=True)
class RainfallClimatologyConfig:
    min_years: int = 10
    min_coverage_fraction: float = 1.0
    collection_id: str = "UCSB-CHG/CHIRPS/DAILY"
    leap_day_policy: str = "omit"


@dataclass(frozen=True)
class HistoricalRainfallYear:
    year: int
    period_start: str
    period_end: str
    accumulated_mm: float | None
    expected_days: int
    available_days: int
    coverage_fraction: float
    quality_flag: str
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class RainfallClimatologyBaseline:
    baseline: Baseline
    percentile_20: float | None
    percentile_50: float | None
    percentile_80: float | None
    included_years: tuple[int, ...]
    excluded_years: tuple[dict[str, Any], ...]
    yearly_observations: tuple[HistoricalRainfallYear, ...]

    @property
    def region_id(self) -> str:
        return self.baseline.region_id

    @property
    def indicator(self) -> str:
        return self.baseline.indicator

    @property
    def unit(self) -> str:
        return self.baseline.unit

    @property
    def mean(self) -> float | None:
        return self.baseline.mean

    @property
    def median(self) -> float | None:
        return self.baseline.median

    @property
    def stddev(self) -> float | None:
        return self.baseline.stddev

    @property
    def quality_flag(self) -> str:
        return self.baseline.quality_flag

    @property
    def metadata(self) -> dict[str, Any]:
        return self.baseline.metadata

    @property
    def baseline_version(self) -> str:
        return str(self.baseline.metadata["baseline_version"])


def compute_rainfall_climatology(
    region_id: str,
    period_start: str,
    period_end: str,
    *,
    years: Iterable[int],
    adapter: RainfallAdapter,
    config: RainfallClimatologyConfig | None = None,
) -> RainfallClimatologyBaseline:
    resolved_config = config or RainfallClimatologyConfig()
    _validate_config(resolved_config)
    current_start = _parse_utc_datetime(period_start, "period_start")
    current_end = _parse_utc_datetime(period_end, "period_end")
    if current_start > current_end:
        raise RainfallClimatologyError("period_start must be before or equal to period_end")

    requested_years = _normalize_years(years)
    region = get_region(region_id)
    rainfall_config = RainfallCollectionConfig(collection_id=resolved_config.collection_id)
    included: list[HistoricalRainfallYear] = []
    excluded: list[dict[str, Any]] = []
    yearly_observations: list[HistoricalRainfallYear] = []

    for year in requested_years:
        equivalent = _equivalent_period_for_year(current_start, current_end, year, resolved_config)
        if equivalent is None:
            excluded.append({"year": year, "reason": "invalid_equivalent_window"})
            continue
        year_start, year_end = equivalent
        expected_days = (year_end.date() - year_start.date()).days + 1
        start_iso = _format_utc(year_start)
        end_iso = _format_utc(year_end)
        result = adapter.query_rainfall(region.geometry, start_iso, end_iso, rainfall_config)
        observation = _observation_from_result(result, year, year_start, year_end, expected_days)
        yearly_observations.append(observation)
        if observation.exclusion_reason:
            excluded.append({"year": year, "reason": observation.exclusion_reason})
            continue
        if observation.coverage_fraction < resolved_config.min_coverage_fraction:
            excluded.append(
                {
                    "year": year,
                    "reason": "insufficient_coverage",
                    "coverage_fraction": observation.coverage_fraction,
                }
            )
            continue
        included.append(observation)

    values = [item.accumulated_mm for item in included if item.accumulated_mm is not None]
    if len(values) != len(included):
        raise RainfallClimatologyError("included rainfall years require accumulated values")

    period_start_out, period_end_out = _baseline_period(
        current_start,
        current_end,
        requested_years,
        resolved_config,
    )
    metadata = _metadata(
        region_id=region.id,
        period_start=period_start,
        period_end=period_end,
        years=requested_years,
        config=resolved_config,
        included_years=[item.year for item in included],
        excluded_years=excluded,
    )

    if len(values) < resolved_config.min_years:
        return _build_result(
            region_id=region.id,
            period_start=period_start_out,
            period_end=period_end_out,
            baseline_start_year=min(requested_years),
            baseline_end_year=max(requested_years),
            config=resolved_config,
            quality_flag="insufficient_history",
            values=[],
            metadata=metadata,
            included=included,
            excluded=excluded,
            yearly_observations=yearly_observations,
        )

    return _build_result(
        region_id=region.id,
        period_start=period_start_out,
        period_end=period_end_out,
        baseline_start_year=min(requested_years),
        baseline_end_year=max(requested_years),
        config=resolved_config,
        quality_flag="ok",
        values=values,
        metadata=metadata,
        included=included,
        excluded=excluded,
        yearly_observations=yearly_observations,
    )


def _build_result(
    *,
    region_id: str,
    period_start: str,
    period_end: str,
    baseline_start_year: int,
    baseline_end_year: int,
    config: RainfallClimatologyConfig,
    quality_flag: str,
    values: list[float],
    metadata: dict[str, Any],
    included: list[HistoricalRainfallYear],
    excluded: list[dict[str, Any]],
    yearly_observations: list[HistoricalRainfallYear],
) -> RainfallClimatologyBaseline:
    if values:
        percentile_20 = _percentile(values, 20)
        percentile_50 = _percentile(values, 50)
        percentile_80 = _percentile(values, 80)
        mean = statistics.fmean(values)
        median = statistics.median(values)
        stddev = statistics.pstdev(values) if len(values) >= 2 else None
    else:
        percentile_20 = None
        percentile_50 = None
        percentile_80 = None
        mean = None
        median = None
        stddev = None
    metadata.update(
        {
            "percentile_20": percentile_20,
            "percentile_50": percentile_50,
            "percentile_80": percentile_80,
            "included_years": [item.year for item in included],
            "excluded_years": list(excluded),
            "sample_size": len(included),
            "min_years": config.min_years,
            "min_coverage_fraction": config.min_coverage_fraction,
        }
    )
    baseline = Baseline(
        region_id=region_id,
        indicator="rainfall_mm",
        period_start=period_start,
        period_end=period_end,
        baseline_start_year=baseline_start_year,
        baseline_end_year=baseline_end_year,
        mean=mean,
        median=median,
        stddev=stddev,
        observations=len(included),
        unit="mm",
        source=config.collection_id,
        quality_flag=quality_flag,
        is_simulated=False,
        metadata=metadata,
    )
    baseline.validate()
    return RainfallClimatologyBaseline(
        baseline=baseline,
        percentile_20=percentile_20,
        percentile_50=percentile_50,
        percentile_80=percentile_80,
        included_years=tuple(item.year for item in included),
        excluded_years=tuple(dict(item) for item in excluded),
        yearly_observations=tuple(yearly_observations),
    )


def _observation_from_result(
    result: RainfallQueryResult,
    year: int,
    requested_start: datetime,
    requested_end: datetime,
    expected_days: int,
) -> HistoricalRainfallYear:
    actual_start = _parse_utc_datetime(result.actual_period_start, "actual_period_start")
    actual_end = _parse_utc_datetime(result.actual_period_end, "actual_period_end")
    if actual_start != requested_start or actual_end != requested_end:
        raise RainfallClimatologyError("adapter result period does not match requested period")
    _validate_result(result, expected_days)
    coverage_fraction = result.available_days / expected_days
    reason = None
    quality_flag = "ok"
    if result.valid_pixel_count == 0 or result.available_days == 0 or result.accumulated_mm is None:
        reason = "no_data"
        quality_flag = "no_data"
    return HistoricalRainfallYear(
        year=year,
        period_start=result.actual_period_start,
        period_end=result.actual_period_end,
        accumulated_mm=result.accumulated_mm,
        expected_days=expected_days,
        available_days=result.available_days,
        coverage_fraction=coverage_fraction,
        quality_flag=quality_flag,
        exclusion_reason=reason,
    )


def _validate_config(config: RainfallClimatologyConfig) -> None:
    if config.min_years <= 0:
        raise RainfallClimatologyError("min_years must be positive")
    if not 0 < config.min_coverage_fraction <= 1:
        raise RainfallClimatologyError("min_coverage_fraction must be inside (0, 1]")
    if not config.collection_id:
        raise RainfallClimatologyError("collection_id is required")
    if config.leap_day_policy != "omit":
        raise RainfallClimatologyError("unsupported leap_day_policy")


def _validate_result(result: RainfallQueryResult, expected_days: int) -> None:
    if expected_days <= 0:
        raise RainfallClimatologyError("expected_days must be positive")
    if result.available_days < 0:
        raise RainfallClimatologyError("available_days must be non-negative")
    if result.available_days > expected_days:
        raise RainfallClimatologyError("available_days cannot exceed expected_days")
    if result.valid_pixel_count < 0 or result.total_pixel_count < 0:
        raise RainfallClimatologyError("pixel counts must be non-negative")
    if result.valid_pixel_count > result.total_pixel_count:
        raise RainfallClimatologyError("valid_pixel_count cannot exceed total_pixel_count")
    if result.accumulated_mm is not None:
        if not math.isfinite(result.accumulated_mm) or result.accumulated_mm < 0:
            raise RainfallClimatologyError("accumulated rainfall must be non-negative and finite")
        if result.available_days == 0:
            raise RainfallClimatologyError("available_days is required when accumulated_mm exists")


def _equivalent_period_for_year(
    current_start: datetime,
    current_end: datetime,
    year: int,
    config: RainfallClimatologyConfig,
) -> tuple[datetime, datetime] | None:
    try:
        start = current_start.replace(year=year)
        end_year = year + (current_end.year - current_start.year)
        end = current_end.replace(year=end_year)
    except ValueError:
        if config.leap_day_policy == "omit":
            return None
        raise
    if start > end:
        raise RainfallClimatologyError("equivalent period is inverted")
    return start, end


def _baseline_period(
    current_start: datetime,
    current_end: datetime,
    years: list[int],
    config: RainfallClimatologyConfig,
) -> tuple[str, str]:
    valid_periods = [
        period
        for year in years
        if (period := _equivalent_period_for_year(current_start, current_end, year, config)) is not None
    ]
    if not valid_periods:
        raise RainfallClimatologyError("no valid equivalent windows")
    return _format_utc(valid_periods[0][0]), _format_utc(valid_periods[-1][1])


def _normalize_years(years: Iterable[int]) -> list[int]:
    normalized = sorted(set(years))
    if not normalized:
        raise RainfallClimatologyError("years are required")
    for year in normalized:
        if not isinstance(year, int) or isinstance(year, bool):
            raise RainfallClimatologyError("years must be integers")
    return normalized


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    if not ordered:
        raise RainfallClimatologyError("percentile requires values")
    position = (len(ordered) - 1) * (percentile / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _metadata(
    *,
    region_id: str,
    period_start: str,
    period_end: str,
    years: list[int],
    config: RainfallClimatologyConfig,
    included_years: list[int],
    excluded_years: list[dict[str, Any]],
) -> dict[str, Any]:
    version_input = "|".join(
        [
            region_id,
            "rainfall_mm",
            period_start,
            period_end,
            ",".join(str(year) for year in years),
            ",".join(str(year) for year in included_years),
            config.collection_id,
            str(config.min_years),
            str(config.min_coverage_fraction),
        ]
    )
    return {
        "baseline_version": hashlib.sha256(version_input.encode("utf-8")).hexdigest()[:16],
        "collection_id": config.collection_id,
        "target_period_start": period_start,
        "target_period_end": period_end,
        "requested_years": list(years),
        "included_years": list(included_years),
        "excluded_years": list(excluded_years),
        "aggregation": "sum",
    }


def _parse_utc_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RainfallClimatologyError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise RainfallClimatologyError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    utc_value = value.astimezone(UTC)
    if utc_value.time() == datetime.min.time():
        return f"{utc_value.date().isoformat()}T00:00:00Z"
    return utc_value.isoformat().replace("+00:00", "Z")

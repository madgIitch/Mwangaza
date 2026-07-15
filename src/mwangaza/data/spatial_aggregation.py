from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from mwangaza.contracts import INDICATOR_UNITS
from mwangaza.regions import Region, get_region


class SpatialAggregationError(ValueError):
    pass


@dataclass(frozen=True)
class SpatialAggregationConfig:
    source: str
    unit: str
    scale_meters: int = 5_000
    max_regions: int = 16
    max_remote_pixels: int = 1_000_000
    min_coverage_fraction: float = 0.5
    percentiles: tuple[int, ...] = (10, 25, 50, 75, 90)
    numeric_tolerance: float = 1e-9


@dataclass(frozen=True)
class SpatialAggregateQueryResult:
    mean: float | None
    median: float | None
    percentiles: dict[int, float] = field(default_factory=dict)
    valid_area: float | None = None
    total_area: float | None = None
    coverage_fraction: float | None = None
    is_simulated: bool = False
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class SpatialAggregate:
    region_id: str
    indicator: str
    unit: str
    period_start: str
    period_end: str
    source: str
    quality_flag: str
    mean: float | None
    median: float | None
    percentiles: dict[int, float]
    valid_area: float | None
    total_area: float | None
    coverage_fraction: float | None
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["percentiles"] = {
            str(key): value for key, value in sorted(self.percentiles.items())
        }
        return payload


class SpatialAggregationAdapter(Protocol):
    def aggregate_region(
        self,
        geometry: dict[str, Any],
        region_id: str,
        indicator: str,
        period_start: str,
        period_end: str,
        config: SpatialAggregationConfig,
    ) -> SpatialAggregateQueryResult:
        ...


def aggregate_regions(
    region_ids: list[str] | tuple[str, ...],
    indicator: str,
    period_start: str,
    period_end: str,
    *,
    adapter: SpatialAggregationAdapter,
    config: SpatialAggregationConfig,
) -> tuple[SpatialAggregate, ...]:
    _validate_config(config, indicator)
    _validate_period(period_start, period_end)
    regions = _resolve_regions(region_ids, config)

    aggregates: list[SpatialAggregate] = []
    for region in sorted(regions, key=lambda item: item.id):
        _validate_analytic_geometry(region)
        result = adapter.aggregate_region(
            region.geometry,
            region.id,
            indicator,
            period_start,
            period_end,
            config,
        )
        aggregates.append(
            _to_aggregate(region, indicator, period_start, period_end, result, config)
        )
    return tuple(aggregates)


def _to_aggregate(
    region: Region,
    indicator: str,
    period_start: str,
    period_end: str,
    result: SpatialAggregateQueryResult,
    config: SpatialAggregationConfig,
) -> SpatialAggregate:
    _validate_query_result(result, config)
    coverage_fraction = _coverage_fraction(result)
    metadata: dict[str, Any] = {
        "scale_meters": config.scale_meters,
        "max_remote_pixels": config.max_remote_pixels,
        "min_coverage_fraction": config.min_coverage_fraction,
        "numeric_tolerance": config.numeric_tolerance,
        "requested_percentiles": list(config.percentiles),
        "coverage_available": coverage_fraction is not None,
        "region_source": region.source,
        "region_source_version": region.source_version,
        "geometry_role": "analytic",
    }
    if result.metadata:
        metadata.update(result.metadata)

    if result.mean is None or result.median is None:
        return SpatialAggregate(
            region_id=region.id,
            indicator=indicator,
            unit=config.unit,
            period_start=period_start,
            period_end=period_end,
            source=config.source,
            quality_flag="no_data",
            mean=None,
            median=None,
            percentiles={},
            valid_area=result.valid_area,
            total_area=result.total_area,
            coverage_fraction=coverage_fraction,
            is_simulated=result.is_simulated,
            metadata={**metadata, "non_conclusive_reason": "no_data"},
        )

    if coverage_fraction is not None and coverage_fraction < config.min_coverage_fraction:
        quality_flag = "degraded"
        metadata["non_conclusive_reason"] = "coverage_below_threshold"
    else:
        quality_flag = "ok"

    return SpatialAggregate(
        region_id=region.id,
        indicator=indicator,
        unit=config.unit,
        period_start=period_start,
        period_end=period_end,
        source=config.source,
        quality_flag=quality_flag,
        mean=result.mean,
        median=result.median,
        percentiles=dict(sorted(result.percentiles.items())),
        valid_area=result.valid_area,
        total_area=result.total_area,
        coverage_fraction=coverage_fraction,
        is_simulated=result.is_simulated,
        metadata=metadata,
    )


def _resolve_regions(
    region_ids: list[str] | tuple[str, ...],
    config: SpatialAggregationConfig,
) -> tuple[Region, ...]:
    if not region_ids:
        raise SpatialAggregationError("at least one region_id is required")
    normalized = [region_id.strip().lower() for region_id in region_ids]
    if any(not region_id for region_id in normalized):
        raise SpatialAggregationError("region_id values must be non-empty")
    duplicates = sorted({region_id for region_id in normalized if normalized.count(region_id) > 1})
    if duplicates:
        raise SpatialAggregationError(f"duplicate region_id values: {', '.join(duplicates)}")
    if len(normalized) > config.max_regions:
        raise SpatialAggregationError("region count exceeds max_regions")
    return tuple(get_region(region_id) for region_id in normalized)


def _validate_config(config: SpatialAggregationConfig, indicator: str) -> None:
    if indicator not in INDICATOR_UNITS:
        raise SpatialAggregationError(f"unsupported indicator: {indicator}")
    expected_unit = INDICATOR_UNITS[indicator]
    if config.unit != expected_unit:
        raise SpatialAggregationError(
            f"unit {config.unit} is incompatible with indicator {indicator}"
        )
    if not config.source or config.source.startswith("/") or "\\" in config.source:
        raise SpatialAggregationError("source must be a non-sensitive source identifier")
    if config.scale_meters <= 0:
        raise SpatialAggregationError("scale_meters must be positive")
    if config.max_regions <= 0:
        raise SpatialAggregationError("max_regions must be positive")
    if config.max_remote_pixels <= 0:
        raise SpatialAggregationError("max_remote_pixels must be positive")
    if not 0 <= config.min_coverage_fraction <= 1:
        raise SpatialAggregationError("min_coverage_fraction must be inside [0, 1]")
    if config.numeric_tolerance <= 0 or not math.isfinite(config.numeric_tolerance):
        raise SpatialAggregationError("numeric_tolerance must be positive and finite")
    if not config.percentiles:
        raise SpatialAggregationError("at least one percentile is required")
    if any(
        not isinstance(percentile, int) or not 0 <= percentile <= 100
        for percentile in config.percentiles
    ):
        raise SpatialAggregationError("percentiles must be integers inside [0, 100]")


def _validate_query_result(
    result: SpatialAggregateQueryResult,
    config: SpatialAggregationConfig,
) -> None:
    for field_name, value in {
        "mean": result.mean,
        "median": result.median,
        "valid_area": result.valid_area,
        "total_area": result.total_area,
        "coverage_fraction": result.coverage_fraction,
    }.items():
        _validate_optional_finite(field_name, value)
    if result.valid_area is not None and result.valid_area < 0:
        raise SpatialAggregationError("valid_area must be non-negative")
    if result.total_area is not None and result.total_area < 0:
        raise SpatialAggregationError("total_area must be non-negative")
    if (
        result.valid_area is not None
        and result.total_area is not None
        and result.valid_area > result.total_area
    ):
        raise SpatialAggregationError("valid_area cannot exceed total_area")
    if result.coverage_fraction is not None and not 0 <= result.coverage_fraction <= 1:
        raise SpatialAggregationError("coverage_fraction must be inside [0, 1]")
    for percentile in config.percentiles:
        if percentile not in result.percentiles and result.mean is not None:
            raise SpatialAggregationError(f"missing requested percentile: {percentile}")
    for percentile, value in result.percentiles.items():
        if percentile not in config.percentiles:
            raise SpatialAggregationError(f"unexpected percentile: {percentile}")
        _validate_optional_finite(f"percentile_{percentile}", value)


def _coverage_fraction(result: SpatialAggregateQueryResult) -> float | None:
    if result.coverage_fraction is not None:
        return result.coverage_fraction
    if result.valid_area is None or result.total_area is None:
        return None
    if result.total_area == 0:
        return 0.0
    return result.valid_area / result.total_area


def _validate_optional_finite(field_name: str, value: float | None) -> None:
    if value is None:
        return
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise SpatialAggregationError(f"{field_name} must be finite")


def _validate_period(start: str, end: str) -> None:
    start_dt = _parse_utc_datetime(start, "period_start")
    end_dt = _parse_utc_datetime(end, "period_end")
    if start_dt > end_dt:
        raise SpatialAggregationError("period_start must be before or equal to period_end")


def _parse_utc_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SpatialAggregationError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise SpatialAggregationError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)


def _validate_analytic_geometry(region: Region) -> None:
    if not region.geometry:
        raise SpatialAggregationError(f"{region.id}: analytic geometry is empty")
    if region.geometry == region.ui_geometry:
        raise SpatialAggregationError(
            f"{region.id}: analytic geometry must differ from ui_geometry"
        )


__all__ = [
    "SpatialAggregate",
    "SpatialAggregateQueryResult",
    "SpatialAggregationAdapter",
    "SpatialAggregationConfig",
    "SpatialAggregationError",
    "aggregate_regions",
]

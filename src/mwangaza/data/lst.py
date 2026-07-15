from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from mwangaza.contracts import IndicatorObservation
from mwangaza.regions import get_region

DEFAULT_LST_COLLECTION = "MODIS/061/MOD11A2"
KELVIN_TO_CELSIUS_OFFSET = -273.15


class LstProcessingError(ValueError):
    pass


@dataclass(frozen=True)
class LstCollectionConfig:
    collection_id: str = DEFAULT_LST_COLLECTION
    scale: float = 0.02
    offset: float = 0.0
    min_valid_celsius: float = -90.0
    max_valid_celsius: float = 80.0
    min_coverage_fraction: float = 0.0


@dataclass(frozen=True)
class LstQueryResult:
    mean_c: float | None
    median_c: float | None
    valid_pixel_count: int
    total_pixel_count: int
    actual_period_start: str
    actual_period_end: str
    is_simulated: bool = False
    metadata: dict[str, Any] | None = None


class LstAdapter(Protocol):
    def query_lst(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: LstCollectionConfig,
    ) -> LstQueryResult:
        ...


def summarize_lst_raw_values(
    raw_values: list[float | int | None],
    quality_mask: list[bool],
    *,
    period_start: str,
    period_end: str,
    config: LstCollectionConfig | None = None,
    is_simulated: bool = False,
) -> LstQueryResult:
    resolved_config = config or LstCollectionConfig()
    _validate_config(resolved_config)
    if len(raw_values) != len(quality_mask):
        raise LstProcessingError("raw_values and quality_mask must have the same length")

    converted: list[float] = []
    for raw, is_quality_pixel in zip(raw_values, quality_mask, strict=True):
        if raw is None or not is_quality_pixel:
            continue
        if not isinstance(raw, int | float) or isinstance(raw, bool) or not math.isfinite(raw):
            raise LstProcessingError("raw LST values must be finite")
        celsius = float(raw) * resolved_config.scale + resolved_config.offset + KELVIN_TO_CELSIUS_OFFSET
        if not math.isfinite(celsius):
            raise LstProcessingError("converted LST values must be finite")
        converted.append(celsius)

    return LstQueryResult(
        mean_c=statistics.fmean(converted) if converted else None,
        median_c=statistics.median(converted) if converted else None,
        valid_pixel_count=len(converted),
        total_pixel_count=len(raw_values),
        actual_period_start=period_start,
        actual_period_end=period_end,
        is_simulated=is_simulated,
        metadata={
            "scale": resolved_config.scale,
            "offset": resolved_config.offset,
            "kelvin_to_celsius_offset": KELVIN_TO_CELSIUS_OFFSET,
            "quality_masked_pixels": len(raw_values) - len(converted),
        },
    )


def compute_current_lst(
    region_id: str,
    period_start: str,
    period_end: str,
    *,
    adapter: LstAdapter,
    config: LstCollectionConfig | None = None,
) -> IndicatorObservation:
    requested_start = _parse_utc_datetime(period_start, "period_start")
    requested_end = _parse_utc_datetime(period_end, "period_end")
    if requested_start > requested_end:
        raise LstProcessingError("period_start must be before or equal to period_end")

    resolved_config = config or LstCollectionConfig()
    _validate_config(resolved_config)
    region = get_region(region_id)
    result = adapter.query_lst(region.geometry, period_start, period_end, resolved_config)
    _validate_query_result(result)

    actual_start = _parse_utc_datetime(result.actual_period_start, "actual_period_start")
    actual_end = _parse_utc_datetime(result.actual_period_end, "actual_period_end")
    if actual_start != requested_start or actual_end != requested_end:
        raise LstProcessingError("adapter result period does not match requested period")

    coverage_fraction = result.valid_pixel_count / result.total_pixel_count if result.total_pixel_count else 0.0
    metadata: dict[str, Any] = {
        "mean_c": result.mean_c,
        "median_c": result.median_c,
        "valid_pixel_count": result.valid_pixel_count,
        "total_pixel_count": result.total_pixel_count,
        "coverage_fraction": coverage_fraction,
        "actual_period_start": result.actual_period_start,
        "actual_period_end": result.actual_period_end,
        "collection_id": resolved_config.collection_id,
        "aggregation": "regional_mean",
        "scale": resolved_config.scale,
        "offset": resolved_config.offset,
        "kelvin_to_celsius_offset": KELVIN_TO_CELSIUS_OFFSET,
        "min_valid_celsius": resolved_config.min_valid_celsius,
        "max_valid_celsius": resolved_config.max_valid_celsius,
    }
    if result.metadata:
        metadata.update(result.metadata)

    if result.valid_pixel_count == 0 or result.mean_c is None:
        return _observation(region.id, result, resolved_config, "no_data", None, metadata)

    if _is_physically_invalid(result.mean_c, resolved_config):
        metadata["invalid_reason"] = "mean_c_outside_physical_range"
        return _observation(region.id, result, resolved_config, "invalid", None, metadata)

    if result.median_c is not None and _is_physically_invalid(result.median_c, resolved_config):
        metadata["invalid_reason"] = "median_c_outside_physical_range"
        return _observation(region.id, result, resolved_config, "invalid", None, metadata)

    quality_flag = "degraded" if coverage_fraction < resolved_config.min_coverage_fraction else "ok"
    return _observation(region.id, result, resolved_config, quality_flag, result.mean_c, metadata)


def _observation(
    region_id: str,
    result: LstQueryResult,
    config: LstCollectionConfig,
    quality_flag: str,
    value: float | None,
    metadata: dict[str, Any],
) -> IndicatorObservation:
    return IndicatorObservation(
        region_id=region_id,
        indicator="lst_c",
        period_start=result.actual_period_start,
        period_end=result.actual_period_end,
        value=value,
        unit="celsius",
        source=config.collection_id,
        quality_flag=quality_flag,
        is_simulated=result.is_simulated,
        metadata=metadata,
    )


def _validate_config(config: LstCollectionConfig) -> None:
    if not config.collection_id:
        raise LstProcessingError("collection_id is required")
    for field_name, value in {
        "scale": config.scale,
        "offset": config.offset,
        "min_valid_celsius": config.min_valid_celsius,
        "max_valid_celsius": config.max_valid_celsius,
        "min_coverage_fraction": config.min_coverage_fraction,
    }.items():
        if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
            raise LstProcessingError(f"{field_name} must be finite")
    if config.scale <= 0:
        raise LstProcessingError("scale must be positive")
    if config.min_valid_celsius >= config.max_valid_celsius:
        raise LstProcessingError("physical temperature range is inverted")
    if not 0 <= config.min_coverage_fraction <= 1:
        raise LstProcessingError("min_coverage_fraction must be inside [0, 1]")


def _validate_query_result(result: LstQueryResult) -> None:
    if result.valid_pixel_count < 0 or result.total_pixel_count < 0:
        raise LstProcessingError("pixel counts must be non-negative")
    if result.valid_pixel_count > result.total_pixel_count:
        raise LstProcessingError("valid_pixel_count cannot exceed total_pixel_count")
    if not result.actual_period_start or not result.actual_period_end:
        raise LstProcessingError("actual LST period is required")
    for field_name, value in {"mean_c": result.mean_c, "median_c": result.median_c}.items():
        if value is not None and (not isinstance(value, int | float) or not math.isfinite(value)):
            raise LstProcessingError(f"{field_name} must be finite")
    if result.mean_c is not None and result.valid_pixel_count == 0:
        raise LstProcessingError("valid_pixel_count is required when mean_c exists")


def _is_physically_invalid(value: float, config: LstCollectionConfig) -> bool:
    return value < config.min_valid_celsius or value > config.max_valid_celsius


def _parse_utc_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LstProcessingError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise LstProcessingError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from mwangaza.config import load_settings
from mwangaza.contracts import IndicatorObservation
from mwangaza.regions import get_region

DEFAULT_RAINFALL_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"


class RainfallProcessingError(ValueError):
    pass


@dataclass(frozen=True)
class RainfallCollectionConfig:
    collection_id: str = DEFAULT_RAINFALL_COLLECTION
    max_missing_days: int = 0

    @classmethod
    def from_settings(cls) -> RainfallCollectionConfig:
        settings = load_settings()
        return cls(collection_id=settings.rainfall_collection)


@dataclass(frozen=True)
class RainfallQueryResult:
    accumulated_mm: float | None
    available_days: int
    actual_period_start: str
    actual_period_end: str
    valid_pixel_count: int = 1
    total_pixel_count: int = 1
    is_simulated: bool = False
    metadata: dict[str, Any] | None = None


class RainfallAdapter(Protocol):
    def query_rainfall(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: RainfallCollectionConfig,
    ) -> RainfallQueryResult:
        ...


def summarize_rainfall_daily_values(
    daily_values_mm: list[float | int | None],
    *,
    period_start: str,
    period_end: str,
    valid_pixel_count: int = 1,
    total_pixel_count: int = 1,
    is_simulated: bool = False,
) -> RainfallQueryResult:
    values: list[float] = []
    for value in daily_values_mm:
        if value is None:
            continue
        if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
            raise RainfallProcessingError("daily rainfall values must be finite")
        if value < 0:
            raise RainfallProcessingError("daily rainfall values must be non-negative")
        values.append(float(value))
    return RainfallQueryResult(
        accumulated_mm=sum(values) if values else None,
        available_days=len(values),
        actual_period_start=period_start,
        actual_period_end=period_end,
        valid_pixel_count=valid_pixel_count,
        total_pixel_count=total_pixel_count,
        is_simulated=is_simulated,
    )


def compute_current_rainfall(
    region_id: str,
    period_start: str,
    period_end: str,
    *,
    adapter: RainfallAdapter,
    config: RainfallCollectionConfig | None = None,
) -> IndicatorObservation:
    requested_start = _parse_utc_datetime(period_start, "period_start")
    requested_end = _parse_utc_datetime(period_end, "period_end")
    if requested_start > requested_end:
        raise RainfallProcessingError("period_start must be before or equal to period_end")

    resolved_config = config or RainfallCollectionConfig.from_settings()
    _validate_config(resolved_config)
    expected_days = (requested_end.date() - requested_start.date()).days + 1
    if expected_days <= 0:
        raise RainfallProcessingError("expected_days must be positive")

    region = get_region(region_id)
    result = adapter.query_rainfall(region.geometry, period_start, period_end, resolved_config)
    _validate_query_result(result, expected_days)

    actual_start = _parse_utc_datetime(result.actual_period_start, "actual_period_start")
    actual_end = _parse_utc_datetime(result.actual_period_end, "actual_period_end")
    if actual_start != requested_start or actual_end != requested_end:
        raise RainfallProcessingError("adapter result period does not match requested period")

    missing_days = expected_days - result.available_days
    coverage_fraction = result.available_days / expected_days
    incomplete_period = missing_days > resolved_config.max_missing_days
    metadata: dict[str, Any] = {
        "expected_days": expected_days,
        "available_days": result.available_days,
        "missing_days": missing_days,
        "coverage_fraction": coverage_fraction,
        "incomplete_period": incomplete_period,
        "max_missing_days": resolved_config.max_missing_days,
        "valid_pixel_count": result.valid_pixel_count,
        "total_pixel_count": result.total_pixel_count,
        "actual_period_start": result.actual_period_start,
        "actual_period_end": result.actual_period_end,
        "collection_id": resolved_config.collection_id,
        "aggregation": "sum",
    }
    if result.metadata:
        metadata.update(result.metadata)

    if result.valid_pixel_count == 0 or result.available_days == 0 or result.accumulated_mm is None:
        return IndicatorObservation(
            region_id=region.id,
            indicator="rainfall_mm",
            period_start=result.actual_period_start,
            period_end=result.actual_period_end,
            value=None,
            unit="mm",
            source=resolved_config.collection_id,
            quality_flag="no_data",
            is_simulated=result.is_simulated,
            metadata=metadata,
        )

    quality_flag = "degraded" if incomplete_period else "ok"
    return IndicatorObservation(
        region_id=region.id,
        indicator="rainfall_mm",
        period_start=result.actual_period_start,
        period_end=result.actual_period_end,
        value=result.accumulated_mm,
        unit="mm",
        source=resolved_config.collection_id,
        quality_flag=quality_flag,
        is_simulated=result.is_simulated,
        metadata=metadata,
    )


def _validate_config(config: RainfallCollectionConfig) -> None:
    if not config.collection_id:
        raise RainfallProcessingError("collection_id is required")
    if config.max_missing_days < 0:
        raise RainfallProcessingError("max_missing_days must be non-negative")


def _validate_query_result(result: RainfallQueryResult, expected_days: int) -> None:
    if result.available_days < 0:
        raise RainfallProcessingError("available_days must be non-negative")
    if result.available_days > expected_days:
        raise RainfallProcessingError("available_days cannot exceed expected_days")
    if result.valid_pixel_count < 0 or result.total_pixel_count < 0:
        raise RainfallProcessingError("pixel counts must be non-negative")
    if result.valid_pixel_count > result.total_pixel_count:
        raise RainfallProcessingError("valid_pixel_count cannot exceed total_pixel_count")
    if not result.actual_period_start or not result.actual_period_end:
        raise RainfallProcessingError("actual rainfall period is required")
    if result.accumulated_mm is not None:
        if not math.isfinite(result.accumulated_mm) or result.accumulated_mm < 0:
            raise RainfallProcessingError("accumulated rainfall must be non-negative and finite")
        if result.available_days == 0:
            raise RainfallProcessingError("available_days is required when accumulated_mm exists")


def _parse_utc_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RainfallProcessingError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise RainfallProcessingError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)

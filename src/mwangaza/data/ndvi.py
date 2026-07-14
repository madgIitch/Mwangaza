from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from mwangaza.config import load_settings
from mwangaza.contracts import IndicatorObservation
from mwangaza.regions import get_region

DEFAULT_NDVI_COLLECTION = "MODIS/061/MOD13Q1"
DEFAULT_NDVI_BAND = "NDVI"
DEFAULT_QA_BAND = "SummaryQA"
DEFAULT_SCALE_FACTOR = 0.0001
DEFAULT_VALID_QA_VALUES = (0,)


class NdviProcessingError(ValueError):
    pass


@dataclass(frozen=True)
class NdviCollectionConfig:
    collection_id: str = DEFAULT_NDVI_COLLECTION
    ndvi_band: str = DEFAULT_NDVI_BAND
    qa_band: str = DEFAULT_QA_BAND
    scale_factor: float = DEFAULT_SCALE_FACTOR
    valid_qa_values: tuple[int, ...] = DEFAULT_VALID_QA_VALUES

    @classmethod
    def from_settings(cls) -> NdviCollectionConfig:
        settings = load_settings()
        return cls(collection_id=settings.ndvi_collection)


@dataclass(frozen=True)
class NdviQueryResult:
    mean_raw: float | None
    valid_pixel_count: int
    total_pixel_count: int
    actual_period_start: str
    actual_period_end: str
    is_simulated: bool = False
    metadata: dict[str, Any] | None = None


class NdviAdapter(Protocol):
    def query_ndvi(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: NdviCollectionConfig,
    ) -> NdviQueryResult:
        ...


def summarize_ndvi_pixels(
    pixels: list[dict[str, int | float | None]],
    *,
    period_start: str,
    period_end: str,
    config: NdviCollectionConfig,
    is_simulated: bool = False,
) -> NdviQueryResult:
    values: list[float] = []
    for pixel in pixels:
        qa = pixel.get(config.qa_band)
        raw = pixel.get(config.ndvi_band)
        if qa not in config.valid_qa_values or raw is None:
            continue
        if not isinstance(raw, int | float):
            continue
        values.append(float(raw))
    mean_raw = sum(values) / len(values) if values else None
    return NdviQueryResult(
        mean_raw=mean_raw,
        valid_pixel_count=len(values),
        total_pixel_count=len(pixels),
        actual_period_start=period_start,
        actual_period_end=period_end,
        is_simulated=is_simulated,
    )


def compute_current_ndvi(
    region_id: str,
    period_start: str,
    period_end: str,
    *,
    adapter: NdviAdapter,
    config: NdviCollectionConfig | None = None,
) -> IndicatorObservation:
    if period_start > period_end:
        raise NdviProcessingError("period_start must be before or equal to period_end")

    resolved_config = config or NdviCollectionConfig.from_settings()
    if not resolved_config.collection_id:
        raise NdviProcessingError("collection_id is required")
    if resolved_config.scale_factor <= 0:
        raise NdviProcessingError("scale_factor must be positive")

    region = get_region(region_id)
    result = adapter.query_ndvi(region.geometry, period_start, period_end, resolved_config)
    _validate_query_result(result)

    valid_fraction = (
        result.valid_pixel_count / result.total_pixel_count
        if result.total_pixel_count > 0 and result.valid_pixel_count > 0
        else 0.0
    )
    metadata = {
        "valid_pixel_fraction": valid_fraction,
        "valid_pixel_count": result.valid_pixel_count,
        "total_pixel_count": result.total_pixel_count,
        "collection_id": resolved_config.collection_id,
        "scale_factor": resolved_config.scale_factor,
        "actual_period_start": result.actual_period_start,
        "actual_period_end": result.actual_period_end,
    }
    if result.metadata:
        metadata.update(result.metadata)

    if result.valid_pixel_count == 0 or result.mean_raw is None:
        return IndicatorObservation(
            region_id=region.id,
            indicator="ndvi",
            period_start=result.actual_period_start,
            period_end=result.actual_period_end,
            value=None,
            unit="index",
            source=resolved_config.collection_id,
            quality_flag="no_data",
            is_simulated=result.is_simulated,
            metadata=metadata,
        )

    value = result.mean_raw * resolved_config.scale_factor
    if value < -1.0 or value > 1.0:
        raise NdviProcessingError("scaled NDVI is outside [-1.0, 1.0]")

    return IndicatorObservation(
        region_id=region.id,
        indicator="ndvi",
        period_start=result.actual_period_start,
        period_end=result.actual_period_end,
        value=value,
        unit="index",
        source=resolved_config.collection_id,
        quality_flag="ok",
        is_simulated=result.is_simulated,
        metadata=metadata,
    )


def _validate_query_result(result: NdviQueryResult) -> None:
    if result.valid_pixel_count < 0 or result.total_pixel_count < 0:
        raise NdviProcessingError("pixel counts must be non-negative")
    if result.valid_pixel_count > result.total_pixel_count:
        raise NdviProcessingError("valid_pixel_count cannot exceed total_pixel_count")
    if not result.actual_period_start or not result.actual_period_end:
        raise NdviProcessingError("actual observation period is required")
    if result.actual_period_start > result.actual_period_end:
        raise NdviProcessingError("actual observation period is inverted")
    if result.valid_pixel_count > 0 and result.mean_raw is None:
        raise NdviProcessingError("mean_raw is required when valid pixels exist")

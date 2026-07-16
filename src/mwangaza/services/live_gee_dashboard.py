from __future__ import annotations

import importlib
import math
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from mwangaza.contracts import IndicatorObservation
from mwangaza.data.indicator_snapshot import build_indicator_snapshot
from mwangaza.data.lst import LstCollectionConfig, LstQueryResult, compute_current_lst
from mwangaza.data.ndvi import NdviCollectionConfig, NdviQueryResult, compute_current_ndvi
from mwangaza.data.rainfall import (
    RainfallCollectionConfig,
    RainfallQueryResult,
    compute_current_rainfall,
)
from mwangaza.gee.auth import check_gee_auth
from mwangaza.quality import evaluate_data_quality
from mwangaza.risk import compute_composite_drought_score

DEFAULT_SCALE_METERS = 5500
DEFAULT_MAX_PIXELS = 1_000_000_000
DEFAULT_LOOKBACK_DAYS = 15


class LiveGeeDashboardError(RuntimeError):
    pass


class RealGeeRegionalAdapter:
    def __init__(
        self,
        ee_module: Any,
        *,
        scale_meters: int = DEFAULT_SCALE_METERS,
        max_pixels: int = DEFAULT_MAX_PIXELS,
    ) -> None:
        self.ee = ee_module
        self.scale_meters = scale_meters
        self.max_pixels = max_pixels

    def query_ndvi(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: NdviCollectionConfig,
    ) -> NdviQueryResult:
        ee_geometry = self.ee.Geometry(geometry)
        collection = self.ee.ImageCollection(config.collection_id).filterDate(
            period_start,
            _exclusive_end(period_end),
        )

        def mask_quality(image: Any) -> Any:
            mask = image.select(config.qa_band).eq(config.valid_qa_values[0])
            return image.updateMask(mask).select(config.ndvi_band)

        image = collection.map(mask_quality).mean()
        mean = _first_number(_reduce(image, self.ee.Reducer.mean(), ee_geometry, self))
        valid_count = _first_int(_reduce(image, self.ee.Reducer.count(), ee_geometry, self))
        return NdviQueryResult(
            mean_raw=mean,
            valid_pixel_count=valid_count,
            total_pixel_count=valid_count,
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
            metadata=_metadata(self.scale_meters),
        )

    def query_rainfall(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: RainfallCollectionConfig,
    ) -> RainfallQueryResult:
        ee_geometry = self.ee.Geometry(geometry)
        collection = self.ee.ImageCollection(config.collection_id).filterDate(
            period_start,
            _exclusive_end(period_end),
        )
        image = collection.select("precipitation").sum()
        accumulated = _first_number(_reduce(image, self.ee.Reducer.mean(), ee_geometry, self))
        valid_count = _first_int(_reduce(image, self.ee.Reducer.count(), ee_geometry, self))
        return RainfallQueryResult(
            accumulated_mm=accumulated,
            available_days=int(collection.size().getInfo() or 0),
            actual_period_start=period_start,
            actual_period_end=period_end,
            valid_pixel_count=valid_count,
            total_pixel_count=valid_count,
            is_simulated=False,
            metadata=_metadata(self.scale_meters),
        )

    def query_lst(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: LstCollectionConfig,
    ) -> LstQueryResult:
        ee_geometry = self.ee.Geometry(geometry)
        collection = self.ee.ImageCollection(config.collection_id).filterDate(
            period_start,
            _exclusive_end(period_end),
        )
        image = collection.select("LST_Day_1km").mean()
        mean_raw = _first_number(_reduce(image, self.ee.Reducer.mean(), ee_geometry, self))
        median_raw = _first_number(_reduce(image, self.ee.Reducer.median(), ee_geometry, self))
        valid_count = _first_int(_reduce(image, self.ee.Reducer.count(), ee_geometry, self))
        return LstQueryResult(
            mean_c=_lst_raw_to_celsius(mean_raw, config) if mean_raw is not None else None,
            median_c=_lst_raw_to_celsius(median_raw, config) if median_raw is not None else None,
            valid_pixel_count=valid_count,
            total_pixel_count=valid_count,
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
            metadata={**_metadata(self.scale_meters), "raw_band": "LST_Day_1km"},
        )


def load_live_gee_dashboard_payloads(
    *,
    region_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    scale_meters: int = DEFAULT_SCALE_METERS,
    ee_module: Any | None = None,
) -> list[dict[str, Any]]:
    auth = check_gee_auth(ee_module=ee_module)
    if auth.status != "ok":
        raise LiveGeeDashboardError(auth.message)

    module = ee_module or importlib.import_module("ee")
    end = period_end or _default_period_end()
    start = period_start or _default_period_start(end)
    target_region = (region_id or os.environ.get("MWANGAZA_DASHBOARD_REGION_ID") or "som").lower()
    adapter = RealGeeRegionalAdapter(module, scale_meters=scale_meters)
    return build_live_gee_payloads(target_region, start, end, adapter=adapter)


def build_live_gee_payloads(
    region_id: str,
    period_start: str,
    period_end: str,
    *,
    adapter: RealGeeRegionalAdapter,
) -> list[dict[str, Any]]:
    signals: tuple[IndicatorObservation, ...] = (
        compute_current_ndvi(region_id, period_start, period_end, adapter=adapter, config=NdviCollectionConfig()),
        compute_current_rainfall(
            region_id,
            period_start,
            period_end,
            adapter=adapter,
            config=RainfallCollectionConfig(max_missing_days=3),
        ),
        compute_current_lst(region_id, period_start, period_end, adapter=adapter, config=LstCollectionConfig()),
    )
    snapshot = build_indicator_snapshot(
        region_id,
        period_start,
        period_end,
        signals,
        expected_indicators=("ndvi", "rainfall_mm", "lst_c"),
    )
    quality = evaluate_data_quality(snapshot, now=datetime.now(UTC))
    risk = compute_composite_drought_score(snapshot, quality)
    payloads = [risk.to_dict(), snapshot.to_dict(), *(signal.to_dict() for signal in signals)]
    for payload in payloads:
        metadata = payload.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["source_mode"] = "live"
            metadata["smoke_source"] = "real_gee"
            metadata["updated_at"] = metadata.get("updated_at", _utc_now())
    return payloads


def _reduce(image: Any, reducer: Any, geometry: Any, adapter: RealGeeRegionalAdapter) -> dict[str, Any]:
    value = image.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=adapter.scale_meters,
        maxPixels=adapter.max_pixels,
    ).getInfo()
    return value if isinstance(value, dict) else {}


def _metadata(scale_meters: int) -> dict[str, Any]:
    return {"updated_at": _utc_now(), "source_mode": "live", "scale_meters": scale_meters}


def _exclusive_end(period_end: str) -> str:
    parsed = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
    return (parsed + timedelta(days=1)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _default_period_end() -> str:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _default_period_start(period_end: str) -> str:
    end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
    return (end - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _first_number(values: dict[str, Any]) -> float | None:
    for value in values.values():
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    return None


def _first_int(values: dict[str, Any]) -> int:
    value = _first_number(values)
    return max(0, int(value or 0))


def _lst_raw_to_celsius(value: float, config: LstCollectionConfig) -> float:
    return value * config.scale + config.offset - 273.15


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "LiveGeeDashboardError",
    "RealGeeRegionalAdapter",
    "build_live_gee_payloads",
    "load_live_gee_dashboard_payloads",
]

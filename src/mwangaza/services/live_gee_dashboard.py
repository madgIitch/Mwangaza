from __future__ import annotations

import importlib
import math
import os
from calendar import monthrange
from datetime import UTC, datetime, timedelta
from typing import Any

from mwangaza.config import ConfigurationError, load_settings
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
from mwangaza.observability import emit
from mwangaza.quality import evaluate_data_quality
from mwangaza.regions import ADM1_LEVEL, COUNTRY_LEVEL, PILOT_LEVEL, get_region, list_regions
from mwangaza.risk import compute_composite_drought_score

DEFAULT_SCALE_METERS = 5500
DEFAULT_ADM1_SCALE_METERS = 1000
DEFAULT_MAX_PIXELS = 1_000_000_000
DEFAULT_LOOKBACK_DAYS = 15
DEFAULT_TREND_MONTHS = 24


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

    def latest_collection_date(self, collection_id: str) -> str:
        millis = self.ee.ImageCollection(collection_id).aggregate_max("system:time_start").getInfo()
        if not isinstance(millis, int | float):
            raise LiveGeeDashboardError(f"collection has no available images: {collection_id}")
        return (
            datetime.fromtimestamp(float(millis) / 1000, UTC)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def query_adm1_values(
        self,
        regions: tuple[Any, ...],
        period_start: str,
        period_end: str,
    ) -> dict[str, dict[str, float | None]]:
        is_adm1_batch = bool(regions) and all(
            getattr(region, "level", None) == ADM1_LEVEL for region in regions
        )
        reduction_scale = (
            min(self.scale_meters, DEFAULT_ADM1_SCALE_METERS)
            if is_adm1_batch
            else self.scale_meters
        )
        ndvi_config = NdviCollectionConfig()
        rainfall_config = RainfallCollectionConfig(max_missing_days=3)
        lst_config = LstCollectionConfig()
        features = self.ee.FeatureCollection([
            self.ee.Feature(self.ee.Geometry(region.geometry), {"region_id": region.id})
            for region in regions
        ])
        ndvi_collection = self.ee.ImageCollection(ndvi_config.collection_id).filterDate(
            period_start,
            _exclusive_end(period_end),
        )

        def mask_quality(image: Any) -> Any:
            valid_qa_values = (
                tuple(dict.fromkeys((*ndvi_config.valid_qa_values, 1)))
                if is_adm1_batch
                else ndvi_config.valid_qa_values
            )
            qa = image.select(ndvi_config.qa_band)
            mask = qa.remap(list(valid_qa_values), [1] * len(valid_qa_values), 0).eq(1)
            return image.updateMask(mask).select(ndvi_config.ndvi_band)

        ndvi = ndvi_collection.map(mask_quality).mean().multiply(ndvi_config.scale_factor).rename("ndvi")
        rainfall = (
            self.ee.ImageCollection(rainfall_config.collection_id)
            .filterDate(period_start, _exclusive_end(period_end))
            .select("precipitation")
            .sum()
            .rename("rainfall_mm")
        )
        lst = (
            self.ee.ImageCollection(lst_config.collection_id)
            .filterDate(period_start, _exclusive_end(period_end))
            .select("LST_Day_1km")
            .mean()
            .multiply(lst_config.scale)
            .add(lst_config.offset - 273.15)
            .rename("lst_c")
        )
        values = (
            ndvi.addBands(rainfall)
            .addBands(lst)
            .reduceRegions(
                collection=features,
                reducer=self.ee.Reducer.mean(),
                scale=reduction_scale,
                tileScale=2,
                maxPixelsPerRegion=self.max_pixels,
            )
            .getInfo()
        )
        rows = values.get("features", []) if isinstance(values, dict) else []
        result: dict[str, dict[str, float | None]] = {}
        for feature in rows:
            properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
            region_id = properties.get("region_id") if isinstance(properties, dict) else None
            if not isinstance(region_id, str):
                continue
            result[region_id] = {
                "ndvi": _optional_finite(properties.get("ndvi")),
                "rainfall_mm": _optional_finite(properties.get("rainfall_mm")),
                "lst_c": _optional_finite(properties.get("lst_c")),
            }
        return result

    def query_time_series_values(
        self,
        regions: tuple[Any, ...],
        windows: tuple[tuple[str, str], ...],
    ) -> dict[tuple[str, str, str], dict[str, float | None]]:
        """Resolve every national monthly window in one Earth Engine request."""
        ndvi_config = NdviCollectionConfig()
        rainfall_config = RainfallCollectionConfig(max_missing_days=3)
        lst_config = LstCollectionConfig()
        features = self.ee.FeatureCollection([
            self.ee.Feature(self.ee.Geometry(region.geometry), {"region_id": region.id})
            for region in regions
        ])
        reduced_windows = []
        for period_start, period_end in windows:
            ndvi_collection = self.ee.ImageCollection(ndvi_config.collection_id).filterDate(
                period_start, _exclusive_end(period_end)
            )

            def mask_quality(image: Any) -> Any:
                qa = image.select(ndvi_config.qa_band)
                mask = qa.remap(list(ndvi_config.valid_qa_values), [1] * len(ndvi_config.valid_qa_values), 0).eq(1)
                return image.updateMask(mask).select(ndvi_config.ndvi_band)

            ndvi = ndvi_collection.map(mask_quality).mean().multiply(ndvi_config.scale_factor).rename("ndvi")
            rainfall = (
                self.ee.ImageCollection(rainfall_config.collection_id)
                .filterDate(period_start, _exclusive_end(period_end))
                .select("precipitation")
                .sum()
                .rename("rainfall_mm")
            )
            lst = (
                self.ee.ImageCollection(lst_config.collection_id)
                .filterDate(period_start, _exclusive_end(period_end))
                .select("LST_Day_1km")
                .mean()
                .multiply(lst_config.scale)
                .add(lst_config.offset - 273.15)
                .rename("lst_c")
            )
            reduced = ndvi.addBands(rainfall).addBands(lst).reduceRegions(
                collection=features,
                reducer=self.ee.Reducer.mean(),
                scale=self.scale_meters,
                tileScale=2,
                maxPixelsPerRegion=self.max_pixels,
            ).map(lambda feature, start=period_start, end=period_end: feature.set({
                "period_start": start,
                "period_end": end,
            }))
            reduced_windows.append(reduced)
        values = self.ee.FeatureCollection(reduced_windows).flatten().getInfo()
        rows = values.get("features", []) if isinstance(values, dict) else []
        result: dict[tuple[str, str, str], dict[str, float | None]] = {}
        for feature in rows:
            properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
            if not isinstance(properties, dict):
                continue
            region_id = properties.get("region_id")
            period_start = properties.get("period_start")
            period_end = properties.get("period_end")
            if not all(isinstance(value, str) for value in (region_id, period_start, period_end)):
                continue
            result[(region_id, period_start, period_end)] = {
                "ndvi": _optional_finite(properties.get("ndvi")),
                "rainfall_mm": _optional_finite(properties.get("rainfall_mm")),
                "lst_c": _optional_finite(properties.get("lst_c")),
            }
        return result


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
    target_region = (region_id or os.environ.get("MWANGAZA_DASHBOARD_REGION_ID") or "som").lower()
    adapter = RealGeeRegionalAdapter(module, scale_meters=scale_meters)
    start, end = resolve_live_gee_period(adapter, period_start=period_start, period_end=period_end)
    region_ids = (target_region,) if region_id is not None else dashboard_live_region_ids(target_region)
    adm1_region_ids = dashboard_live_adm1_region_ids()
    if period_start is not None or period_end is not None:
        payloads = build_live_gee_payloads_for_regions(region_ids, start, end, adapter=adapter)
        payloads.extend(build_live_gee_payloads_for_adm1_regions(adm1_region_ids, start, end, adapter=adapter))
        return payloads
    current_start = _default_period_start(end)
    payloads = build_live_gee_payloads_for_regions(region_ids, current_start, end, adapter=adapter)
    for historical_start, historical_end in comparable_period_windows(end, years=2):
        try:
            payloads.extend(build_live_gee_payloads_for_regions(region_ids, historical_start, historical_end, adapter=adapter))
        except Exception as exc:
            emit(
                "Historical GEE batch query failed",
                level="WARNING",
                component="live_gee_dashboard",
                period_end=historical_end,
                error_type=type(exc).__name__,
            )
    try:
        payloads.extend(build_live_gee_trend_payloads_for_regions(
            region_ids,
            end,
            adapter=adapter,
            month_count=_live_trend_months(),
        ))
    except Exception as exc:
        emit(
            "Regional trend GEE batch query failed; retrying each region independently",
            level="WARNING",
            component="live_gee_dashboard",
            region_count=len(region_ids),
            error_type=type(exc).__name__,
        )
        for retry_region_id in region_ids:
            try:
                payloads.extend(build_live_gee_trend_payloads_for_regions(
                    (retry_region_id,),
                    end,
                    adapter=adapter,
                    month_count=_live_trend_months(),
                ))
            except Exception as region_exc:
                emit(
                    "Single-region trend GEE query failed",
                    level="WARNING",
                    component="live_gee_dashboard",
                    region_id=retry_region_id,
                    error_type=type(region_exc).__name__,
                )
    try:
        payloads.extend(
            build_live_gee_payloads_for_adm1_regions(adm1_region_ids, _default_period_start(end), end, adapter=adapter)
        )
    except Exception as exc:
        emit(
            "ADM1 GEE module failed without discarding national payloads",
            level="WARNING",
            component="live_gee_dashboard",
            error_type=type(exc).__name__,
        )
    return payloads


def dashboard_live_region_ids(selected_region_id: str | None = None) -> tuple[str, ...]:
    target_region = (selected_region_id or os.environ.get("MWANGAZA_DASHBOARD_REGION_ID") or "som").lower()
    return _ordered_region_ids(target_region, _enabled_dashboard_region_ids())


def dashboard_live_adm1_region_ids() -> tuple[str, ...]:
    if os.environ.get("MWANGAZA_GEE_ADM1_ENABLED", "true").strip().lower() in {"0", "false", "no", "off"}:
        return ()
    configured = os.environ.get("MWANGAZA_GEE_ADM1_COUNTRIES", "").strip()
    configured_iso3 = {item.strip().upper() for item in configured.split(",") if item.strip()}
    regions = list_regions(level=ADM1_LEVEL, include_administrative=True)
    if not configured_iso3:
        try:
            configured_iso3 = set(load_settings().enabled_countries)
        except ConfigurationError:
            configured_iso3 = {region.iso3 for region in regions}
    return tuple(region.id for region in regions if region.iso3 in configured_iso3)


def resolve_live_gee_period(
    adapter: Any,
    *,
    period_start: str | None = None,
    period_end: str | None = None,
) -> tuple[str, str]:
    end = period_end or _latest_common_collection_date(adapter)
    start = period_start or _default_period_start(end)
    return start, end


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
    payloads = [
        _json_safe(risk.to_dict()),
        _json_safe(snapshot.to_dict()),
        *(_json_safe(signal.to_dict()) for signal in signals),
    ]
    region = get_region(region_id)
    for payload in payloads:
        metadata = payload.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["source_mode"] = "live"
            metadata["smoke_source"] = "real_gee"
            metadata["updated_at"] = metadata.get("updated_at", _utc_now())
            metadata["region_level"] = region.level
            metadata["parent_region_id"] = region.parent_id
            if region.level == ADM1_LEVEL:
                metadata["boundary_id"] = region.metadata.get("boundary_id")
                metadata["boundary_iso"] = region.metadata.get("boundary_iso")
                metadata["geometry_source"] = f"{region.source} {region.source_version}"
    return payloads


def build_live_gee_payloads_for_regions(
    region_ids: tuple[str, ...],
    period_start: str,
    period_end: str,
    *,
    adapter: RealGeeRegionalAdapter,
) -> list[dict[str, Any]]:
    if hasattr(adapter, "query_adm1_values"):
        regions = tuple(get_region(region_id) for region_id in region_ids)
        try:
            values_by_region = adapter.query_adm1_values(regions, period_start, period_end)
        except Exception as exc:
            emit(
                "Regional GEE batch query failed",
                level="WARNING",
                component="live_gee_dashboard",
                region_count=len(regions),
                error_type=type(exc).__name__,
            )
        else:
            batch_payloads: list[dict[str, Any]] = []
            for region in regions:
                values = values_by_region.get(region.id)
                if values is None:
                    continue
                batch_payloads.extend(
                    _build_region_payloads_from_values(region, values, period_start, period_end)
                )
            return batch_payloads

    payloads: list[dict[str, Any]] = []
    for region_id in region_ids:
        try:
            payloads.extend(build_live_gee_payloads(region_id, period_start, period_end, adapter=adapter))
        except Exception as exc:
            emit(
                "Regional GEE query failed",
                level="WARNING",
                component="live_gee_dashboard",
                region_id=region_id,
                error_type=type(exc).__name__,
            )
    return payloads


def build_live_gee_payloads_for_adm1_regions(
    region_ids: tuple[str, ...],
    period_start: str,
    period_end: str,
    *,
    adapter: RealGeeRegionalAdapter,
) -> list[dict[str, Any]]:
    if not region_ids:
        return []
    if hasattr(adapter, "query_adm1_values"):
        regions = tuple(get_region(region_id) for region_id in region_ids)
        values_by_region: dict[str, dict[str, float | None]] | None = None
        try:
            values_by_region = adapter.query_adm1_values(regions, period_start, period_end)
        except Exception as exc:
            emit(
                "ADM1 GEE batch query failed",
                level="WARNING",
                component="live_gee_dashboard",
                region_count=len(regions),
                error_type=type(exc).__name__,
            )
        if values_by_region is not None:
            batch_payloads: list[dict[str, Any]] = []
            for region in regions:
                values = values_by_region.get(region.id)
                if values is None:
                    continue
                batch_payloads.extend(
                    _build_region_payloads_from_values(region, values, period_start, period_end)
                )
            return batch_payloads

    payloads: list[dict[str, Any]] = []
    for region_id in region_ids:
        try:
            payloads.extend(build_live_gee_payloads(region_id, period_start, period_end, adapter=adapter))
        except Exception as exc:
            emit(
                "ADM1 GEE query failed",
                level="WARNING",
                component="live_gee_dashboard",
                region_id=region_id,
                error_type=type(exc).__name__,
            )
            continue
    return payloads


def _build_region_payloads_from_values(
    region: Any,
    values: dict[str, float | None],
    period_start: str,
    period_end: str,
) -> list[dict[str, Any]]:
    configs = {
        "ndvi": ("index", NdviCollectionConfig().collection_id),
        "rainfall_mm": ("mm", RainfallCollectionConfig().collection_id),
        "lst_c": ("celsius", LstCollectionConfig().collection_id),
    }
    signals = tuple(
        IndicatorObservation(
            region_id=region.id,
            indicator=indicator,
            period_start=period_start,
            period_end=period_end,
            value=values.get(indicator),
            unit=unit,
            source=source,
            quality_flag="ok" if values.get(indicator) is not None else "no_data",
            is_simulated=False,
            metadata={
                "updated_at": _utc_now(),
                "source_mode": "live",
                "aggregation_mode": "reduceRegions",
                "coverage_fraction": 1.0 if values.get(indicator) is not None else 0.0,
                "summary_qa_values": [0, 1] if region.level == ADM1_LEVEL and indicator == "ndvi" else None,
            },
        )
        for indicator, (unit, source) in configs.items()
    )
    snapshot = build_indicator_snapshot(
        region.id,
        period_start,
        period_end,
        signals,
        expected_indicators=("ndvi", "rainfall_mm", "lst_c"),
    )
    quality = evaluate_data_quality(snapshot, now=datetime.now(UTC))
    risk = compute_composite_drought_score(snapshot, quality)
    payloads = [
        _json_safe(risk.to_dict()),
        _json_safe(snapshot.to_dict()),
        *(_json_safe(signal.to_dict()) for signal in signals),
    ]
    for payload in payloads:
        metadata = payload.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata.update({
                "source_mode": "live",
                "smoke_source": "real_gee",
                "aggregation_mode": "reduceRegions",
                "region_level": region.level,
                "parent_region_id": region.parent_id,
                "boundary_id": region.metadata.get("boundary_id"),
                "boundary_iso": region.metadata.get("boundary_iso"),
                "geometry_source": f"{region.source} {region.source_version}",
            })
    return payloads


def build_live_gee_payloads_for_recent_periods(
    region_ids: tuple[str, ...],
    latest_period_end: str,
    *,
    adapter: RealGeeRegionalAdapter,
    point_count: int = DEFAULT_TREND_MONTHS,
    history_years: int = 0,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    payloads.extend(build_live_gee_trend_payloads_for_regions(
        region_ids, latest_period_end, adapter=adapter, month_count=point_count
    ))
    for period_start, period_end in comparable_period_windows(latest_period_end, years=history_years):
        payloads.extend(build_live_gee_payloads_for_regions(region_ids, period_start, period_end, adapter=adapter))
    return payloads


def build_live_gee_trend_payloads_for_regions(
    region_ids: tuple[str, ...],
    latest_period_end: str,
    *,
    adapter: RealGeeRegionalAdapter,
    month_count: int = DEFAULT_TREND_MONTHS,
) -> list[dict[str, Any]]:
    regions = tuple(get_region(region_id) for region_id in region_ids)
    windows = monthly_period_windows(latest_period_end, month_count=month_count)
    if hasattr(adapter, "query_time_series_values"):
        values_by_period = adapter.query_time_series_values(regions, windows)
        payloads: list[dict[str, Any]] = []
        for period_start, period_end in windows:
            for region in regions:
                values = values_by_period.get((region.id, period_start, period_end))
                if values is not None:
                    payloads.extend(_build_trend_payloads_from_values(region, values, period_start, period_end))
        return payloads
    payloads = []
    for period_start, period_end in windows:
        period_payloads = build_live_gee_payloads_for_regions(region_ids, period_start, period_end, adapter=adapter)
        for payload in period_payloads:
            if payload.get("payload_type") != "indicator_observation":
                continue
            metadata = payload.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata.update({"trend_series": True, "aggregation_period": "monthly"})
            payloads.append(payload)
    return payloads


def _build_trend_payloads_from_values(
    region: Any,
    values: dict[str, float | None],
    period_start: str,
    period_end: str,
) -> list[dict[str, Any]]:
    configs = {
        "ndvi": ("index", NdviCollectionConfig().collection_id),
        "rainfall_mm": ("mm", RainfallCollectionConfig().collection_id),
        "lst_c": ("celsius", LstCollectionConfig().collection_id),
    }
    return [
        _json_safe(IndicatorObservation(
            region_id=region.id,
            indicator=indicator,
            period_start=period_start,
            period_end=period_end,
            value=values.get(indicator),
            unit=unit,
            source=source,
            quality_flag="ok" if values.get(indicator) is not None else "no_data",
            is_simulated=False,
            metadata={
                "updated_at": period_end,
                "source_mode": "live",
                "aggregation_mode": "reduceRegions",
                "aggregation_period": "monthly",
                "trend_series": True,
            },
        ).to_dict())
        for indicator, (unit, source) in configs.items()
    ]


def comparable_period_windows(latest_period_end: str, *, years: int = 2) -> tuple[tuple[str, str], ...]:
    bounded_years = max(0, min(int(years), 5))
    end = datetime.fromisoformat(latest_period_end.replace("Z", "+00:00")).astimezone(UTC)
    windows = []
    for offset in range(1, bounded_years + 1):
        try:
            historical_end = end.replace(year=end.year - offset)
        except ValueError:
            historical_end = end.replace(year=end.year - offset, day=28)
        historical_start = historical_end - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1)
        windows.append((
            historical_start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            historical_end.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
        ))
    return tuple(windows)


def recent_period_windows(
    latest_period_end: str,
    *,
    point_count: int = DEFAULT_TREND_MONTHS,
) -> tuple[tuple[str, str], ...]:
    return monthly_period_windows(latest_period_end, month_count=point_count)


def monthly_period_windows(
    latest_period_end: str,
    *,
    month_count: int = DEFAULT_TREND_MONTHS,
) -> tuple[tuple[str, str], ...]:
    bounded_count = max(1, min(int(month_count), 24))
    end = datetime.fromisoformat(latest_period_end.replace("Z", "+00:00")).astimezone(UTC)
    windows: list[tuple[str, str]] = []
    for index in range(bounded_count):
        period_end = _shift_month(end, -index)
        period_start = _shift_month(end, -(index + 1)) + timedelta(days=1)
        windows.append(
            (
                period_start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
                period_end.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
            )
        )
    return tuple(windows)


def _shift_month(value: datetime, offset: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def _reduce(image: Any, reducer: Any, geometry: Any, adapter: RealGeeRegionalAdapter) -> dict[str, Any]:
    value = image.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=adapter.scale_meters,
        maxPixels=adapter.max_pixels,
    ).getInfo()
    return value if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


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


def _latest_common_collection_date(adapter: Any) -> str:
    dates = (
        adapter.latest_collection_date(NdviCollectionConfig().collection_id),
        adapter.latest_collection_date(RainfallCollectionConfig().collection_id),
        adapter.latest_collection_date(LstCollectionConfig().collection_id),
    )
    return str(min(dates))


def _enabled_country_region_ids() -> tuple[str, ...]:
    countries = list_regions(level=COUNTRY_LEVEL, include_pilots=False)
    try:
        enabled_iso3 = set(load_settings().enabled_countries)
    except ConfigurationError:
        enabled_iso3 = {country.iso3 for country in countries}
    return tuple(country.id for country in countries if country.iso3 in enabled_iso3)


def _enabled_dashboard_region_ids() -> tuple[str, ...]:
    countries = _enabled_country_region_ids()
    enabled_country_ids = set(countries)
    try:
        enabled_iso3 = set(load_settings().enabled_countries)
    except ConfigurationError:
        enabled_iso3 = {region.iso3 for region in list_regions(level=COUNTRY_LEVEL, include_pilots=False)}
    pilots = tuple(
        region.id
        for region in list_regions(level=PILOT_LEVEL, include_pilots=True)
        if region.iso3 in enabled_iso3 and region.parent_id in enabled_country_ids
    )
    return (*countries, *pilots)


def _ordered_region_ids(selected_region_id: str, region_ids: tuple[str, ...]) -> tuple[str, ...]:
    selected = selected_region_id.lower()
    ordered = [selected]
    ordered.extend(region_id for region_id in region_ids if region_id != selected)
    return tuple(dict.fromkeys(ordered))


def _live_trend_months() -> int:
    raw = os.environ.get(
        "MWANGAZA_LIVE_TREND_MONTHS",
        os.environ.get("MWANGAZA_LIVE_TREND_POINTS", str(DEFAULT_TREND_MONTHS)),
    )
    try:
        return max(12, min(int(raw), 24))
    except ValueError:
        return DEFAULT_TREND_MONTHS


def _first_number(values: dict[str, Any]) -> float | None:
    for value in values.values():
        if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    return None


def _optional_finite(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value) else None


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
    "build_live_gee_payloads_for_regions",
    "build_live_gee_payloads_for_adm1_regions",
    "build_live_gee_payloads_for_recent_periods",
    "build_live_gee_trend_payloads_for_regions",
    "comparable_period_windows",
    "dashboard_live_region_ids",
    "dashboard_live_adm1_region_ids",
    "load_live_gee_dashboard_payloads",
    "monthly_period_windows",
    "recent_period_windows",
    "resolve_live_gee_period",
]

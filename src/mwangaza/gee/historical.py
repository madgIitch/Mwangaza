from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from mwangaza.probabilistic.backfill import DekadalWindow, HistoricalSignalRow

RAIN_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
NDVI_COLLECTION = "MODIS/061/MOD13Q1"
LST_COLLECTION = "MODIS/061/MOD11A2"


class EarthEngineHistoricalAdapter:
    def __init__(self, ee_module: Any, *, scale_meters: int = 5500) -> None:
        self.ee = ee_module
        self.scale_meters = scale_meters

    def fetch(
        self, region: object, windows: tuple[DekadalWindow, ...]
    ) -> tuple[HistoricalSignalRow, ...]:
        geometry = self.ee.Geometry(getattr(region, "geometry"))
        features = [self._feature(geometry, window) for window in windows]
        payload = self.ee.FeatureCollection(features).getInfo()
        raw_rows = payload.get("features", []) if isinstance(payload, dict) else []
        by_start = {
            item.get("properties", {}).get("period_start"): item.get("properties", {})
            for item in raw_rows
            if isinstance(item, dict)
        }
        return tuple(
            self._row(region, window, by_start.get(window.period_start, {}))
            for window in windows
        )

    def _feature(self, geometry: Any, window: DekadalWindow) -> Any:
        exclusive_end = self.ee.Date(window.period_end).advance(1, "day")
        rain_collection = self.ee.ImageCollection(RAIN_COLLECTION).filterDate(
            window.period_start, exclusive_end
        )
        rain_reduction = (
            rain_collection.select("precipitation")
            .sum()
            .reduceRegion(
                reducer=self.ee.Reducer.mean(),
                geometry=geometry,
                scale=self.scale_meters,
                maxPixels=1_000_000_000,
                tileScale=2,
            )
        )
        rain = self.ee.Algorithms.If(
            rain_reduction.contains("precipitation"),
            rain_reduction.get("precipitation"),
            None,
        )

        ndvi_collection = (
            self.ee.ImageCollection(NDVI_COLLECTION)
            .filterDate("2000-01-01", exclusive_end)
            .sort("system:time_start", False)
        )
        ndvi_image = self.ee.Image(ndvi_collection.first())
        ndvi_reduction = (
            ndvi_image.updateMask(ndvi_image.select("SummaryQA").lte(1))
            .select("NDVI")
            .multiply(0.0001)
            .reduceRegion(
                reducer=self.ee.Reducer.mean(),
                geometry=geometry,
                scale=self.scale_meters,
                maxPixels=1_000_000_000,
                tileScale=2,
            )
        )
        ndvi = self.ee.Algorithms.If(
            ndvi_reduction.contains("NDVI"), ndvi_reduction.get("NDVI"), None
        )

        lst_collection = (
            self.ee.ImageCollection(LST_COLLECTION)
            .filterDate("2000-01-01", exclusive_end)
            .sort("system:time_start", False)
        )
        lst_image = self.ee.Image(lst_collection.first())
        lst_reduction = (
            lst_image.select("LST_Day_1km")
            .multiply(0.02)
            .subtract(273.15)
            .reduceRegion(
                reducer=self.ee.Reducer.mean(),
                geometry=geometry,
                scale=self.scale_meters,
                maxPixels=1_000_000_000,
                tileScale=2,
            )
        )
        lst = self.ee.Algorithms.If(
            lst_reduction.contains("LST_Day_1km"),
            lst_reduction.get("LST_Day_1km"),
            None,
        )
        return self.ee.Feature(
            None,
            {
                "period_start": window.period_start,
                "rainfall_mm": rain,
                "rainfall_available_days": rain_collection.size(),
                "ndvi": ndvi,
                "ndvi_observed_at_ms": ndvi_image.get("system:time_start"),
                "lst_c": lst,
                "lst_observed_at_ms": lst_image.get("system:time_start"),
            },
        )

    def _row(
        self, region: object, window: DekadalWindow, values: dict[str, Any]
    ) -> HistoricalSignalRow:
        ndvi_at = _millis_date(values.get("ndvi_observed_at_ms"))
        lst_at = _millis_date(values.get("lst_observed_at_ms"))
        rainfall = _number(values.get("rainfall_mm"))
        ndvi = _number(values.get("ndvi"))
        lst = _number(values.get("lst_c"))
        missing = tuple(
            name
            for name, value in (
                ("rainfall_no_data", rainfall),
                ("ndvi_no_data", ndvi),
                ("lst_no_data", lst),
            )
            if value is None
        )
        return HistoricalSignalRow(
            region_id=str(getattr(region, "id")),
            period_start=window.period_start,
            period_end=window.period_end,
            as_of=window.as_of,
            rainfall_mm=rainfall,
            rainfall_available_days=int(values.get("rainfall_available_days") or 0),
            rainfall_observed_at=window.as_of if rainfall is not None else None,
            ndvi=ndvi,
            ndvi_observed_at=ndvi_at,
            ndvi_age_days=_age_days(ndvi_at, window.period_end),
            lst_c=lst,
            lst_observed_at=lst_at,
            lst_age_days=_age_days(lst_at, window.period_end),
            quality_flag="ok" if not missing else "no_data",
            missing_reasons=missing,
            source_mode="live",
            geometry_version=str(getattr(region, "source_version")),
        )


def _millis_date(value: object) -> str | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value) / 1000, UTC).date().isoformat()


def _age_days(observed_at: str | None, period_end: str) -> int | None:
    if observed_at is None:
        return None
    age = (date.fromisoformat(period_end) - date.fromisoformat(observed_at)).days
    if age < 0:
        raise ValueError("upstream observation is in the future")
    return age


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None

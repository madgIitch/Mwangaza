from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from mwangaza.probabilistic.adm1 import Adm1RawRow, SignalObservation
from mwangaza.probabilistic.backfill import DekadalWindow

RAIN_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
NDVI_COLLECTION = "MODIS/061/MOD13Q1"
SPEI_COLLECTION = "CSIC/SPEI/2_11"
FLDAS_COLLECTION = "NASA/FLDAS/NOAH01/C/GL/M/V001"
FORECAST_COLLECTION = "ECMWF/NRT_FORECAST/IFS/OPER"
FORECAST_FIRST_CREATION = datetime(2024, 11, 12, 12, tzinfo=UTC)

SOURCE_VERSIONS = {
    RAIN_COLLECTION: "CHIRPS Daily v2.0",
    NDVI_COLLECTION: "MOD13Q1.061",
    SPEI_COLLECTION: "SPEIbase 2.11",
    FLDAS_COLLECTION: "FLDAS Noah 3.6.1 V001",
    FORECAST_COLLECTION: "ECMWF IFS Open Data",
}


class EarthEngineAdm1AntecedentAdapter:
    """Batched Earth Engine adapter: every remote request contains many ADM1 units."""

    def __init__(self, ee_module: Any, *, scale_meters: int = 11_132) -> None:
        self.ee = ee_module
        self.scale_meters = scale_meters

    def fetch(
        self, regions: tuple[object, ...], windows: tuple[DekadalWindow, ...]
    ) -> tuple[Adm1RawRow, ...]:
        region_features = self.ee.FeatureCollection(
            [
                self.ee.Feature(
                    self.ee.Geometry(getattr(region, "geometry")),
                    {"region_id": str(getattr(region, "id"))},
                )
                for region in regions
            ]
        )
        reductions = [
            self._reduce_window(region_features, window) for window in windows
        ]
        payload = self.ee.FeatureCollection(reductions).flatten().getInfo()
        features = payload.get("features", []) if isinstance(payload, dict) else []
        values_by_key: dict[str, dict[str, Any]] = {}
        for feature in features:
            properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
            key = f"{properties.get('region_id')}:{properties.get('period_start')}"
            values_by_key[key] = properties
        return tuple(
            self._row(
                region,
                window,
                values_by_key.get(f"{getattr(region, 'id')}:{window.period_start}", {}),
            )
            for region in regions
            for window in windows
        )

    def _reduce_window(self, regions: Any, window: DekadalWindow) -> Any:
        exclusive_end = self.ee.Date(window.period_end).advance(1, "day")
        safe_as_of = _window_available_at(window)
        rain_collection = self.ee.ImageCollection(RAIN_COLLECTION).filterDate(
            window.period_start, exclusive_end
        )
        rain = rain_collection.select("precipitation").sum().rename("rainfall_mm")
        rain_days = self.ee.Image.constant(rain_collection.size()).rename(
            "rainfall_available_days"
        )

        ndvi_collection = (
            self.ee.ImageCollection(NDVI_COLLECTION)
            .filterDate(
                exclusive_end.advance(-56, "day"),
                exclusive_end.advance(-16, "day"),
            )
            .sort("system:time_start", False)
        )
        ndvi_raw = self._latest_or_masked(
            ndvi_collection, ("NDVI", "SummaryQA"), ("NDVI", "SummaryQA")
        )
        ndvi = (
            ndvi_raw.select("NDVI")
            .updateMask(ndvi_raw.select("SummaryQA").lte(1))
            .multiply(0.0001)
            .rename("ndvi")
        )

        monthly_cutoff = self.ee.Date.fromYMD(
            self.ee.Date(window.period_end).get("year"),
            self.ee.Date(window.period_end).get("month"),
            1,
        )
        spei_collection = (
            self.ee.ImageCollection(SPEI_COLLECTION)
            .filterDate(monthly_cutoff.advance(-3, "month"), monthly_cutoff)
            .sort("system:time_start", False)
        )
        spei = self._latest_or_masked(
            spei_collection,
            ("SPEI_01_month", "SPEI_03_month", "SPEI_06_month"),
            ("spei_1m", "spei_3m", "spei_6m"),
        )

        fldas_collection = (
            self.ee.ImageCollection(FLDAS_COLLECTION)
            .filterDate(monthly_cutoff.advance(-3, "month"), monthly_cutoff)
            .sort("system:time_start", False)
        )
        fldas = self._latest_or_masked(
            fldas_collection,
            (
                "SoilMoi00_10cm_tavg",
                "SoilMoi10_40cm_tavg",
                "SoilMoi40_100cm_tavg",
                "SoilMoi100_200cm_tavg",
                "Evap_tavg",
            ),
            (
                "soil_moisture_0_10cm",
                "soil_moisture_10_40cm",
                "soil_moisture_40_100cm",
                "soil_moisture_100_200cm",
                "evapotranspiration_rate",
            ),
        )
        rootzone = (
            fldas.select("soil_moisture_0_10cm")
            .multiply(10)
            .add(fldas.select("soil_moisture_10_40cm").multiply(30))
            .add(fldas.select("soil_moisture_40_100cm").multiply(60))
            .add(fldas.select("soil_moisture_100_200cm").multiply(100))
            .divide(200)
            .rename("soil_moisture_rootzone")
        )

        forecast_10d, forecast_10d_collection = self._forecast(safe_as_of, 240)
        forecast_15d, forecast_15d_collection = self._forecast(safe_as_of, 360)
        image = (
            rain.addBands(rain_days)
            .addBands(ndvi)
            .addBands(spei)
            .addBands(fldas.select(("soil_moisture_0_10cm", "evapotranspiration_rate")))
            .addBands(rootzone)
            .addBands(forecast_10d)
            .addBands(forecast_15d)
        )
        metadata = {
            "period_start": window.period_start,
            "period_end": window.period_end,
            "as_of": safe_as_of,
            "ndvi_observed_at_ms": self._latest_time(ndvi_collection),
            "spei_observed_at_ms": self._latest_time(spei_collection),
            "fldas_observed_at_ms": self._latest_time(fldas_collection),
            "forecast_10d_creation_ms": self._latest_property(
                forecast_10d_collection, "creation_time"
            ),
            "forecast_15d_creation_ms": self._latest_property(
                forecast_15d_collection, "creation_time"
            ),
        }
        reduced = image.reduceRegions(
            collection=regions,
            reducer=self.ee.Reducer.mean(),
            scale=self.scale_meters,
            tileScale=4,
        )
        return reduced.map(
            lambda feature: self.ee.Feature(None, self.ee.Feature(feature).toDictionary()).set(
                metadata
            )
        )

    def _latest_or_masked(
        self,
        collection: Any,
        source_bands: tuple[str, ...],
        output_bands: tuple[str, ...],
    ) -> Any:
        fallback = (
            self.ee.Image.constant([0] * len(source_bands))
            .rename(source_bands)
            .updateMask(self.ee.Image.constant(0))
        )
        image = self.ee.Image(
            self.ee.Algorithms.If(collection.size().gt(0), collection.first(), fallback)
        )
        return image.select(source_bands).rename(output_bands)

    def _forecast(self, safe_as_of: str, lead_hours: int) -> tuple[Any, Any]:
        as_of = self.ee.Date(safe_as_of)
        collection = (
            self.ee.ImageCollection(FORECAST_COLLECTION)
            .filter(self.ee.Filter.lte("creation_time", as_of.millis()))
            .filter(self.ee.Filter.gte("creation_time", as_of.advance(-48, "hour").millis()))
            .filter(self.ee.Filter.eq("forecast_hours", lead_hours))
            .filter(self.ee.Filter.eq("model", "ifs"))
            .sort("creation_time", False)
        )
        image = self._latest_or_masked(
            collection, ("total_precipitation_sfc",), (f"forecast_precip_{lead_hours // 24}d_mm",)
        ).multiply(1000)
        return image, collection

    def _latest_time(self, collection: Any) -> Any:
        return self.ee.Algorithms.If(
            collection.size().gt(0),
            self.ee.Image(collection.first()).get("system:time_start"),
            None,
        )

    def _latest_property(self, collection: Any, name: str) -> Any:
        return self.ee.Algorithms.If(
            collection.size().gt(0), self.ee.Image(collection.first()).get(name), None
        )

    def _row(
        self, region: object, window: DekadalWindow, values: dict[str, Any]
    ) -> Adm1RawRow:
        metadata = getattr(region, "metadata")
        safe_as_of = (
            str(values["as_of"])
            if isinstance(values.get("as_of"), str)
            else _window_available_at(window)
        )
        as_of = _parse_time(safe_as_of)
        ndvi_at = _millis_iso(values.get("ndvi_observed_at_ms"))
        ndvi_available = None if ndvi_at is None else ndvi_at + timedelta(days=16)
        spei_at = _millis_iso(values.get("spei_observed_at_ms"))
        fldas_at = _millis_iso(values.get("fldas_observed_at_ms"))
        monthly_available = datetime(as_of.year, as_of.month, 1, tzinfo=UTC)
        signals = {
            "rainfall_mm": _observed(
                values.get("rainfall_mm"),
                unit="mm",
                collection=RAIN_COLLECTION,
                observed_at=as_of,
                available_at=as_of,
                as_of=as_of,
                missing_reason=(
                    "rainfall_collection_empty"
                    if _number(values.get("rainfall_available_days")) == 0
                    else "geometry_no_pixels"
                ),
            ),
            "rainfall_available_days": _observed(
                values.get("rainfall_available_days"),
                unit="days",
                collection=RAIN_COLLECTION,
                observed_at=as_of,
                available_at=as_of,
                as_of=as_of,
                missing_reason="rainfall_collection_empty",
                integer=True,
            ),
            "ndvi": _observed(
                values.get("ndvi"),
                unit="ndvi_fraction",
                collection=NDVI_COLLECTION,
                observed_at=ndvi_at,
                available_at=ndvi_available,
                as_of=as_of,
                missing_reason="ndvi_no_pixels",
                collection_missing_reason="ndvi_collection_empty",
                max_age_days=56,
            ),
        }
        for scale in (1, 3, 6):
            signals[f"spei_{scale}m"] = _observed(
                values.get(f"spei_{scale}m"),
                unit="z_score",
                collection=SPEI_COLLECTION,
                observed_at=spei_at,
                available_at=monthly_available,
                as_of=as_of,
                missing_reason="spei_not_available_for_date",
                collection_missing_reason="spei_not_available_for_date",
                max_age_days=70,
            )
        signals["soil_moisture_0_10cm"] = _observed(
            values.get("soil_moisture_0_10cm"),
            unit="volume_fraction",
            collection=FLDAS_COLLECTION,
            observed_at=fldas_at,
            available_at=monthly_available,
            as_of=as_of,
            missing_reason="fldas_not_available_for_date",
            collection_missing_reason="fldas_not_available_for_date",
            max_age_days=70,
        )
        signals["soil_moisture_rootzone"] = _observed(
            values.get("soil_moisture_rootzone"),
            unit="volume_fraction",
            collection=FLDAS_COLLECTION,
            observed_at=fldas_at,
            available_at=monthly_available,
            as_of=as_of,
            missing_reason="fldas_not_available_for_date",
            collection_missing_reason="fldas_not_available_for_date",
            max_age_days=70,
        )
        signals["evapotranspiration_rate"] = _observed(
            values.get("evapotranspiration_rate"),
            unit="kg/m^2/s",
            collection=FLDAS_COLLECTION,
            observed_at=fldas_at,
            available_at=monthly_available,
            as_of=as_of,
            missing_reason="fldas_not_available_for_date",
            collection_missing_reason="fldas_not_available_for_date",
            max_age_days=70,
        )
        for lead_hours in (240, 360):
            name = f"forecast_precip_{lead_hours // 24}d_mm"
            creation = _millis_time(values.get(f"forecast_{lead_hours // 24}d_creation_ms"))
            signals[name] = _forecast_observation(
                values.get(name),
                creation=creation,
                as_of=as_of,
                lead_hours=lead_hours,
            )
        return Adm1RawRow(
            region_id=str(getattr(region, "id")),
            parent_region_id=str(getattr(region, "parent_id")),
            parent_iso3=str(getattr(region, "iso3")),
            boundary_id=str(metadata["boundary_id"]),
            boundary_iso=str(metadata["boundary_iso"]),
            boundary_source=str(getattr(region, "source")),
            boundary_version=str(getattr(region, "source_version")),
            period_start=window.period_start,
            period_end=window.period_end,
            as_of=safe_as_of,
            signals=signals,
        )


def _observed(
    raw_value: object,
    *,
    unit: str,
    collection: str,
    observed_at: datetime | None,
    available_at: datetime | None,
    as_of: datetime,
    missing_reason: str,
    collection_missing_reason: str | None = None,
    max_age_days: int | None = None,
    integer: bool = False,
) -> SignalObservation:
    value = _number(raw_value)
    age = None if observed_at is None else (as_of.date() - observed_at.date()).days
    unavailable = (
        value is None
        or observed_at is None
        or age is None
        or age < 0
        or (available_at is not None and available_at > as_of)
    )
    if available_at is not None and available_at > as_of:
        missing_reason = "not_available_at_as_of"
    if observed_at is None and collection_missing_reason is not None:
        missing_reason = collection_missing_reason
    if max_age_days is not None and age is not None and age > max_age_days:
        unavailable = True
        missing_reason = "collection_gap"
    return SignalObservation(
        value=None if unavailable else int(value) if integer else value,
        unit=unit,
        source_collection=collection,
        source_version=SOURCE_VERSIONS[collection],
        observed_at=None if unavailable else _iso(observed_at),
        available_at=None if unavailable or available_at is None else _iso(available_at),
        age_days=None if unavailable else age,
        lead_hours=None,
        quality="missing" if unavailable else "observed",
        missing_reason=missing_reason if unavailable else None,
    )


def _forecast_observation(
    raw_value: object,
    *,
    creation: datetime | None,
    as_of: datetime,
    lead_hours: int,
) -> SignalObservation:
    value = _number(raw_value)
    supported = as_of >= FORECAST_FIRST_CREATION
    valid = supported and value is not None and creation is not None and creation <= as_of
    reason = "not_available_for_date" if not supported else "forecast_collection_gap"
    return SignalObservation(
        value=value if valid else None,
        unit="mm",
        source_collection=FORECAST_COLLECTION,
        source_version=SOURCE_VERSIONS[FORECAST_COLLECTION],
        observed_at=None,
        available_at=_iso(creation) if valid and creation is not None else None,
        age_days=None,
        lead_hours=lead_hours if valid else None,
        quality="forecast" if valid else "missing",
        missing_reason=None if valid else reason,
    )


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _millis_iso(value: object) -> datetime | None:
    return _millis_time(value)


def _millis_time(value: object) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value) / 1000, UTC)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _window_available_at(window: DekadalWindow) -> str:
    exclusive_end = date.fromisoformat(window.period_end) + timedelta(days=1)
    return datetime.combine(exclusive_end, datetime.min.time(), tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )

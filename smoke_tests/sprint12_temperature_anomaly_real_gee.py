from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "src")

import ee  # type: ignore[import-untyped]

from mwangaza.data.lst import LstCollectionConfig, LstQueryResult, compute_current_lst
from mwangaza.data.temperature_anomaly import (
    LstClimatologyConfig,
    LstYearObservation,
    TemperatureAnomalyConfig,
    compute_lst_climatology,
    compute_temperature_anomaly,
)

REGION_ID = os.getenv("MWANGAZA_SMOKE_REGION_ID", "ken")
COLLECTION = os.getenv("MWANGAZA_SMOKE_LST_COLLECTION", "MODIS/061/MOD11A2")
PRODUCT_VARIANT = os.getenv("MWANGAZA_SMOKE_LST_PRODUCT_VARIANT", "day")
CURRENT_START = os.getenv("MWANGAZA_SMOKE_CURRENT_START", "2024-07-01T00:00:00Z")
CURRENT_END = os.getenv("MWANGAZA_SMOKE_CURRENT_END", "2024-07-31T00:00:00Z")
SEASON_START = os.getenv("MWANGAZA_SMOKE_SEASON_START", "07-01")
SEASON_END = os.getenv("MWANGAZA_SMOKE_SEASON_END", "07-31")
BASELINE_START_YEAR = int(os.getenv("MWANGAZA_SMOKE_BASELINE_START_YEAR", "2019"))
BASELINE_END_YEAR = int(os.getenv("MWANGAZA_SMOKE_BASELINE_END_YEAR", "2023"))
SERVICE_ACCOUNT_JSON_PATH = os.getenv("MWANGAZA_GEE_SERVICE_ACCOUNT_JSON_PATH")


def main() -> int:
    if not SERVICE_ACCOUNT_JSON_PATH:
        raise SystemExit(
            "Set MWANGAZA_GEE_SERVICE_ACCOUNT_JSON_PATH to a service account JSON file before running this smoke test."
        )

    raw_key = Path(SERVICE_ACCOUNT_JSON_PATH).read_text(encoding="utf-8")
    key = json.loads(raw_key)
    project = key["project_id"]
    service_account = key["client_email"]

    credentials = ee.ServiceAccountCredentials(service_account, key_data=raw_key)
    ee.Initialize(credentials, project=project)

    lst_config = LstCollectionConfig(
        collection_id=COLLECTION,
        scale=0.02,
        offset=0.0,
        min_valid_celsius=-90.0,
        max_valid_celsius=80.0,
        min_coverage_fraction=0.01,
    )

    current = compute_current_lst(
        REGION_ID,
        CURRENT_START,
        CURRENT_END,
        adapter=RealGeeCurrentLstAdapter(),
        config=lst_config,
    )
    baseline = compute_lst_climatology(
        REGION_ID,
        SEASON_START,
        SEASON_END,
        CURRENT_START,
        CURRENT_END,
        adapter=RealGeeLstClimatologyAdapter(),
        config=LstClimatologyConfig(
            start_year=BASELINE_START_YEAR,
            end_year=BASELINE_END_YEAR,
            min_years=3,
            collection_id=COLLECTION,
            product_variant=PRODUCT_VARIANT,
            min_valid_celsius=-90.0,
            max_valid_celsius=80.0,
        ),
    )
    anomaly = compute_temperature_anomaly(
        current,
        baseline,
        config=TemperatureAnomalyConfig(zscore_epsilon=0.001),
    )

    assert current.indicator == "lst_c"
    assert current.unit == "celsius"
    assert current.is_simulated is False
    assert current.metadata["product_variant"] == PRODUCT_VARIANT
    assert baseline.indicator == "lst_c"
    assert baseline.unit == "celsius"
    assert baseline.metadata["product_variant"] == PRODUCT_VARIANT
    assert baseline.quality_flag in {"ok", "insufficient_history"}
    assert anomaly.indicator == "lst_c"
    assert anomaly.unit == "celsius"
    assert anomaly.metadata["product_variant"] == PRODUCT_VARIANT
    assert anomaly.quality_flag in {"ok", "degraded", "no_data", "insufficient_history", "invalid"}
    if anomaly.value is not None:
        assert current.value is not None
        assert baseline.mean is not None
        assert math.isclose(anomaly.value, current.value - baseline.mean, rel_tol=0, abs_tol=1e-9)
        assert math.isclose(anomaly.metadata["absolute_anomaly_c"], anomaly.value, rel_tol=0, abs_tol=1e-9)

    output = {
        "current": current.to_dict(),
        "baseline": baseline.to_dict(),
        "anomaly": anomaly.to_dict(),
    }
    _assert_sanitized(output)
    print("SPRINT 12 REAL GEE SMOKE OK")
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


class RealGeeCurrentLstAdapter:
    def query_lst(self, geometry: dict[str, Any], period_start: str, period_end: str, config: LstCollectionConfig) -> LstQueryResult:
        reduced = _reduce_lst(geometry, period_start, period_end, config)
        return LstQueryResult(
            mean_c=reduced["mean_c"],
            median_c=reduced["median_c"],
            valid_pixel_count=reduced["valid_pixel_count"],
            total_pixel_count=reduced["total_pixel_count"],
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
            metadata={
                "image_count": reduced["image_count"],
                "band": reduced["band"],
                "quality_band": reduced["quality_band"],
                "quality_rule": "QC bits 0-1 == 0",
                "product_variant": PRODUCT_VARIANT,
            },
        )


class RealGeeLstClimatologyAdapter:
    def query_lst_year(
        self,
        geometry: dict[str, Any],
        year: int,
        season_start: str,
        season_end: str,
        config: LstClimatologyConfig,
    ) -> LstYearObservation:
        period_start, period_end = _season_period(year, season_start, season_end)
        reduced = _reduce_lst(
            geometry,
            period_start,
            period_end,
            LstCollectionConfig(
                collection_id=config.collection_id,
                scale=0.02,
                offset=0.0,
                min_valid_celsius=config.min_valid_celsius,
                max_valid_celsius=config.max_valid_celsius,
                min_coverage_fraction=0.01,
            ),
        )
        quality_flag = "ok" if reduced["mean_c"] is not None and reduced["valid_pixel_count"] > 0 else "no_data"
        return LstYearObservation(
            year=year,
            mean_c=reduced["mean_c"],
            median_c=reduced["median_c"],
            quality_flag=quality_flag,
            source=config.collection_id,
            metadata={
                "period_start": period_start,
                "period_end": period_end,
                "image_count": reduced["image_count"],
                "valid_pixel_count": reduced["valid_pixel_count"],
                "total_pixel_count": reduced["total_pixel_count"],
                "product_variant": config.product_variant,
            },
        )


def _reduce_lst(
    region_geometry: dict[str, Any],
    period_start: str,
    period_end: str,
    config: LstCollectionConfig,
) -> dict[str, Any]:
    region = ee.Geometry(region_geometry)
    end_exclusive = ee.Date(period_end).advance(1, "day")
    band = "LST_Day_1km" if PRODUCT_VARIANT == "day" else "LST_Night_1km"
    qc_band = "QC_Day" if PRODUCT_VARIANT == "day" else "QC_Night"

    def to_celsius_with_quality(image: Any) -> Any:
        lst = image.select(band)
        qc = image.select(qc_band)
        good_quality = qc.bitwiseAnd(3).eq(0)
        return (
            lst.multiply(config.scale)
            .add(config.offset)
            .subtract(273.15)
            .updateMask(good_quality)
            .rename("lst_c")
            .copyProperties(image, image.propertyNames())
        )

    collection = (
        ee.ImageCollection(config.collection_id)
        .filterDate(period_start, end_exclusive)
        .filterBounds(region)
        .map(to_celsius_with_quality)
    )
    image_count = collection.size().getInfo()
    assert image_count > 0, f"No MODIS LST images found for {period_start} to {period_end}"
    image = collection.mean().clip(region)

    reducer = ee.Reducer.mean().combine(ee.Reducer.median(), sharedInputs=True).combine(
        ee.Reducer.count(),
        sharedInputs=True,
    )
    stats = image.reduceRegion(
        reducer=reducer,
        geometry=region,
        scale=1000,
        maxPixels=100000000,
        bestEffort=True,
    ).getInfo()
    total = ee.Image.constant(1).rename("total").clip(region).reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=region,
        scale=1000,
        maxPixels=100000000,
        bestEffort=True,
    ).getInfo()

    mean_c = stats.get("lst_c_mean")
    median_c = stats.get("lst_c_median")
    return {
        "mean_c": float(mean_c) if mean_c is not None else None,
        "median_c": float(median_c) if median_c is not None else None,
        "valid_pixel_count": int(stats.get("lst_c_count") or 0),
        "total_pixel_count": int(total.get("total") or 0),
        "image_count": image_count,
        "band": band,
        "quality_band": qc_band,
    }


def _season_period(year: int, season_start: str, season_end: str) -> tuple[str, str]:
    sm, sd = [int(x) for x in season_start.split("-")]
    em, ed = [int(x) for x in season_end.split("-")]
    end_year = year + 1 if (em, ed) < (sm, sd) else year
    return (
        f"{year:04d}-{sm:02d}-{sd:02d}T00:00:00Z",
        f"{end_year:04d}-{em:02d}-{ed:02d}T00:00:00Z",
    )


def _assert_sanitized(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, sort_keys=True).lower()
    sensitive_tokens = [
        "private_key",
        "service_account",
        "client_email",
    ]
    for token in sensitive_tokens:
        assert token not in text, f"payload leaked forbidden token: {token}"

    forbidden_fields = {"recommendation", "recommendations", "severity", "action", "actions", "alert", "alerts"}
    for field_path in _field_paths(payload):
        field_name = field_path.rsplit(".", 1)[-1].lower()
        assert field_name not in forbidden_fields, f"payload included forbidden decision field: {field_path}"


def _field_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.append(path)
            paths.extend(_field_paths(item, path))
        return paths
    if isinstance(value, list):
        paths = []
        for index, item in enumerate(value):
            paths.extend(_field_paths(item, f"{prefix}[{index}]"))
        return paths
    return []


if __name__ == "__main__":
    raise SystemExit(main())

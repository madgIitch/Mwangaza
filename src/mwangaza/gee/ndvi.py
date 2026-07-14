from __future__ import annotations

import importlib
from typing import Any

from mwangaza.data.ndvi import NdviCollectionConfig, NdviProcessingError, NdviQueryResult


class EarthEngineNdviAdapter:
    def __init__(self, ee_module: object | None = None) -> None:
        self.ee = ee_module or importlib.import_module("ee")

    def query_ndvi(
        self,
        geometry: dict[str, Any],
        period_start: str,
        period_end: str,
        config: NdviCollectionConfig,
    ) -> NdviQueryResult:
        ee = self.ee
        ee_geometry = ee.Geometry(geometry)
        collection = (
            ee.ImageCollection(config.collection_id)
            .filterBounds(ee_geometry)
            .filterDate(period_start, period_end)
        )
        image = collection.select([config.ndvi_band, config.qa_band]).mean()
        qa = image.select(config.qa_band)
        valid_mask = None
        for qa_value in config.valid_qa_values:
            mask = qa.eq(qa_value)
            valid_mask = mask if valid_mask is None else valid_mask.Or(mask)
        if valid_mask is None:
            raise NdviProcessingError("valid_qa_values cannot be empty")

        ndvi = image.select(config.ndvi_band).updateMask(valid_mask)
        valid_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
            geometry=ee_geometry,
            bestEffort=True,
        ).getInfo()
        total_stats = image.select(config.ndvi_band).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=ee_geometry,
            bestEffort=True,
        ).getInfo()
        mean_raw = valid_stats.get(f"{config.ndvi_band}_mean")
        valid_count = int(valid_stats.get(f"{config.ndvi_band}_count") or 0)
        total_count = int(total_stats.get(config.ndvi_band) or 0)
        return NdviQueryResult(
            mean_raw=float(mean_raw) if mean_raw is not None else None,
            valid_pixel_count=valid_count,
            total_pixel_count=total_count,
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
        )

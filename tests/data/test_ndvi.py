from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mwangaza.data.ndvi import (
    NdviCollectionConfig,
    NdviProcessingError,
    compute_current_ndvi,
    summarize_ndvi_pixels,
)
from mwangaza.regions import get_region


class FakeNdviAdapter:
    def __init__(
        self,
        pixels: list[dict[str, int | float | None]],
        *,
        actual_period_start: str = "2026-07-01T00:00:00Z",
        actual_period_end: str = "2026-07-10T00:00:00Z",
    ) -> None:
        self.pixels = pixels
        self.actual_period_start = actual_period_start
        self.actual_period_end = actual_period_end
        self.calls: list[tuple[dict[str, object], str, str, NdviCollectionConfig]] = []

    def query_ndvi(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: NdviCollectionConfig,
    ) -> object:
        self.calls.append((geometry, period_start, period_end, config))
        return summarize_ndvi_pixels(
            self.pixels,
            period_start=self.actual_period_start,
            period_end=self.actual_period_end,
            config=config,
            is_simulated=True,
        )


class CurrentNdviTests(unittest.TestCase):
    def test_computes_scaled_ndvi_observation(self) -> None:
        adapter = FakeNdviAdapter(
            [
                {"NDVI": 4000, "SummaryQA": 0},
                {"NDVI": 5000, "SummaryQA": 0},
                {"NDVI": 9000, "SummaryQA": 1},
                {"NDVI": None, "SummaryQA": 0},
            ]
        )
        result = compute_current_ndvi(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=adapter,
        )

        self.assertEqual(result.indicator, "ndvi")
        self.assertEqual(result.unit, "index")
        self.assertEqual(result.source, "MODIS/061/MOD13Q1")
        self.assertEqual(result.quality_flag, "ok")
        self.assertAlmostEqual(result.value or 0, 0.45)
        self.assertTrue(-1.0 <= (result.value or 0) <= 1.0)
        self.assertEqual(result.period_start, "2026-07-01T00:00:00Z")
        self.assertEqual(result.period_end, "2026-07-10T00:00:00Z")
        self.assertEqual(result.metadata["valid_pixel_count"], 2)
        self.assertEqual(result.metadata["total_pixel_count"], 4)
        self.assertEqual(result.metadata["valid_pixel_fraction"], 0.5)

    def test_no_valid_pixels_returns_no_data_not_zero(self) -> None:
        adapter = FakeNdviAdapter(
            [
                {"NDVI": 4000, "SummaryQA": 1},
                {"NDVI": None, "SummaryQA": 0},
            ]
        )
        result = compute_current_ndvi(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=adapter,
        )
        self.assertIsNone(result.value)
        self.assertEqual(result.quality_flag, "no_data")
        self.assertEqual(result.metadata["valid_pixel_fraction"], 0.0)

    def test_collection_can_be_changed_by_argument(self) -> None:
        config = NdviCollectionConfig(collection_id="CUSTOM/NDVI", scale_factor=0.001)
        adapter = FakeNdviAdapter([{"NDVI": 250, "SummaryQA": 0}])
        result = compute_current_ndvi(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=adapter,
            config=config,
        )
        self.assertEqual(result.source, "CUSTOM/NDVI")
        self.assertEqual(result.metadata["collection_id"], "CUSTOM/NDVI")
        self.assertAlmostEqual(result.value or 0, 0.25)

    def test_collection_can_be_changed_by_environment_config(self) -> None:
        adapter = FakeNdviAdapter([{"NDVI": 3000, "SummaryQA": 0}])
        with patch.dict(os.environ, {"MWANGAZA_NDVI_COLLECTION": "ENV/NDVI"}, clear=True):
            result = compute_current_ndvi(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-15T00:00:00Z",
                adapter=adapter,
            )
        self.assertEqual(result.source, "ENV/NDVI")

    def test_adapter_receives_region_geometry_and_requested_dates(self) -> None:
        adapter = FakeNdviAdapter([{"NDVI": 1000, "SummaryQA": 0}])
        compute_current_ndvi(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=adapter,
        )
        geometry, start, end, _config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(start, "2026-07-01T00:00:00Z")
        self.assertEqual(end, "2026-07-15T00:00:00Z")

    def test_rejects_scaled_ndvi_outside_expected_range(self) -> None:
        adapter = FakeNdviAdapter([{"NDVI": 20000, "SummaryQA": 0}])
        with self.assertRaisesRegex(NdviProcessingError, "outside"):
            compute_current_ndvi(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-15T00:00:00Z",
                adapter=adapter,
            )

    def test_rejects_inverted_requested_dates(self) -> None:
        adapter = FakeNdviAdapter([{"NDVI": 1000, "SummaryQA": 0}])
        with self.assertRaisesRegex(NdviProcessingError, "period_start"):
            compute_current_ndvi(
                "ken",
                "2026-07-15T00:00:00Z",
                "2026-07-01T00:00:00Z",
                adapter=adapter,
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import unittest

from mwangaza.data.spatial_aggregation import (
    SpatialAggregateQueryResult,
    SpatialAggregationConfig,
    SpatialAggregationError,
    aggregate_regions,
)
from mwangaza.regions import get_region


class FakeSpatialAggregationAdapter:
    def __init__(self, results: dict[str, SpatialAggregateQueryResult]) -> None:
        self.results = results
        self.calls: list[
            tuple[dict[str, object], str, str, str, str, SpatialAggregationConfig]
        ] = []

    def aggregate_region(
        self,
        geometry: dict[str, object],
        region_id: str,
        indicator: str,
        period_start: str,
        period_end: str,
        config: SpatialAggregationConfig,
    ) -> SpatialAggregateQueryResult:
        self.calls.append((geometry, region_id, indicator, period_start, period_end, config))
        return self.results[region_id]


def _config(**overrides: object) -> SpatialAggregationConfig:
    payload = {
        "source": "TEST/NDVI",
        "unit": "index",
        "scale_meters": 1000,
        "max_regions": 4,
        "max_remote_pixels": 100_000,
        "min_coverage_fraction": 0.5,
        "percentiles": (10, 50, 90),
    }
    payload.update(overrides)
    return SpatialAggregationConfig(**payload)


def _result(**overrides: object) -> SpatialAggregateQueryResult:
    payload = {
        "mean": 0.42,
        "median": 0.4,
        "percentiles": {10: 0.2, 50: 0.4, 90: 0.7},
        "valid_area": 80.0,
        "total_area": 100.0,
        "is_simulated": True,
        "metadata": {"adapter": "fake"},
    }
    payload.update(overrides)
    return SpatialAggregateQueryResult(**payload)


class SpatialAggregationTests(unittest.TestCase):
    def test_aggregates_each_region_with_statistics_and_traceability(self) -> None:
        adapter = FakeSpatialAggregationAdapter(
            {"ken": _result(), "som": _result(mean=0.31, median=0.3)}
        )

        results = aggregate_regions(
            ["som", "ken"],
            "ndvi",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=_config(),
        )

        self.assertEqual([item.region_id for item in results], ["ken", "som"])
        first = results[0]
        self.assertEqual(first.indicator, "ndvi")
        self.assertEqual(first.unit, "index")
        self.assertEqual(first.source, "TEST/NDVI")
        self.assertEqual(first.quality_flag, "ok")
        self.assertEqual(first.mean, 0.42)
        self.assertEqual(first.median, 0.4)
        self.assertEqual(first.percentiles, {10: 0.2, 50: 0.4, 90: 0.7})
        self.assertEqual(first.valid_area, 80.0)
        self.assertEqual(first.total_area, 100.0)
        self.assertEqual(first.coverage_fraction, 0.8)
        self.assertEqual(first.metadata["geometry_role"], "analytic")
        self.assertEqual(first.metadata["numeric_tolerance"], 1e-9)
        self.assertEqual(first.to_dict()["percentiles"], {"10": 0.2, "50": 0.4, "90": 0.7})

    def test_adapter_receives_analytic_geometry_not_ui_geometry(self) -> None:
        adapter = FakeSpatialAggregationAdapter({"ken": _result()})

        aggregate_regions(
            ["ken"],
            "ndvi",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=_config(),
        )

        geometry, region_id, indicator, _, _, received_config = adapter.calls[0]
        region = get_region("ken")
        self.assertEqual(region_id, "ken")
        self.assertEqual(indicator, "ndvi")
        self.assertEqual(geometry, region.geometry)
        self.assertNotEqual(geometry, region.ui_geometry)
        self.assertEqual(received_config.scale_meters, 1000)

    def test_low_coverage_marks_degraded_without_inventing_zero(self) -> None:
        adapter = FakeSpatialAggregationAdapter({"ken": _result(valid_area=30.0, total_area=100.0)})

        result = aggregate_regions(
            ["ken"],
            "ndvi",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=_config(min_coverage_fraction=0.5),
        )[0]

        self.assertEqual(result.quality_flag, "degraded")
        self.assertEqual(result.mean, 0.42)
        self.assertEqual(result.coverage_fraction, 0.3)
        self.assertEqual(result.metadata["non_conclusive_reason"], "coverage_below_threshold")

    def test_missing_area_is_explicitly_unavailable(self) -> None:
        adapter = FakeSpatialAggregationAdapter(
            {"ken": _result(valid_area=None, total_area=None, coverage_fraction=None)}
        )

        result = aggregate_regions(
            ["ken"],
            "ndvi",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=_config(),
        )[0]

        self.assertEqual(result.quality_flag, "ok")
        self.assertIsNone(result.valid_area)
        self.assertIsNone(result.total_area)
        self.assertIsNone(result.coverage_fraction)
        self.assertFalse(result.metadata["coverage_available"])

    def test_no_data_is_not_converted_to_zero(self) -> None:
        adapter = FakeSpatialAggregationAdapter(
            {
                "ken": _result(
                    mean=None,
                    median=None,
                    percentiles={},
                    valid_area=0.0,
                    total_area=100.0,
                )
            }
        )

        result = aggregate_regions(
            ["ken"],
            "ndvi",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=_config(),
        )[0]

        self.assertEqual(result.quality_flag, "no_data")
        self.assertIsNone(result.mean)
        self.assertIsNone(result.median)
        self.assertEqual(result.percentiles, {})
        self.assertEqual(result.coverage_fraction, 0.0)

    def test_limits_fail_before_adapter_call(self) -> None:
        adapter = FakeSpatialAggregationAdapter({"ken": _result(), "som": _result()})

        with self.assertRaisesRegex(SpatialAggregationError, "max_regions"):
            aggregate_regions(
                ["ken", "som"],
                "ndvi",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=adapter,
                config=_config(max_regions=1),
            )

        self.assertEqual(adapter.calls, [])

    def test_rejects_unknown_inputs_and_non_finite_values(self) -> None:
        adapter = FakeSpatialAggregationAdapter({"ken": _result(mean=math.inf)})

        with self.assertRaisesRegex(SpatialAggregationError, "unsupported indicator"):
            aggregate_regions(
                ["ken"],
                "unknown",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=adapter,
                config=_config(),
            )
        with self.assertRaisesRegex(SpatialAggregationError, "incompatible"):
            aggregate_regions(
                ["ken"],
                "rainfall_mm",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=adapter,
                config=_config(unit="index"),
            )
        with self.assertRaisesRegex(SpatialAggregationError, "finite"):
            aggregate_regions(
                ["ken"],
                "ndvi",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=adapter,
                config=_config(),
            )

    def test_rejects_missing_requested_percentile_and_duplicate_regions(self) -> None:
        missing_percentile = FakeSpatialAggregationAdapter(
            {"ken": _result(percentiles={10: 0.2, 50: 0.4})}
        )

        with self.assertRaisesRegex(SpatialAggregationError, "missing requested percentile"):
            aggregate_regions(
                ["ken"],
                "ndvi",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=missing_percentile,
                config=_config(),
            )
        with self.assertRaisesRegex(SpatialAggregationError, "duplicate"):
            aggregate_regions(
                ["ken", "ken"],
                "ndvi",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=missing_percentile,
                config=_config(),
            )


if __name__ == "__main__":
    unittest.main()

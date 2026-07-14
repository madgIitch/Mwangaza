from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mwangaza.data.rainfall import (
    RainfallCollectionConfig,
    RainfallProcessingError,
    RainfallQueryResult,
    compute_current_rainfall,
    summarize_rainfall_daily_values,
)
from mwangaza.regions import get_region


class FakeRainfallAdapter:
    def __init__(self, result: RainfallQueryResult) -> None:
        self.result = result
        self.calls: list[tuple[dict[str, object], str, str, RainfallCollectionConfig]] = []

    def query_rainfall(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: RainfallCollectionConfig,
    ) -> RainfallQueryResult:
        self.calls.append((geometry, period_start, period_end, config))
        return self.result


class CurrentRainfallTests(unittest.TestCase):
    def test_computes_accumulated_rainfall_observation(self) -> None:
        result = summarize_rainfall_daily_values(
            [1.5, 2.0, 0.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-03T00:00:00Z",
            valid_pixel_count=5,
            total_pixel_count=6,
            is_simulated=True,
        )
        observation = compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            adapter=FakeRainfallAdapter(result),
        )

        self.assertEqual(observation.indicator, "rainfall_mm")
        self.assertEqual(observation.unit, "mm")
        self.assertEqual(observation.source, "UCSB-CHG/CHIRPS/DAILY")
        self.assertEqual(observation.quality_flag, "ok")
        self.assertAlmostEqual(observation.value or 0.0, 3.5)
        self.assertEqual(observation.metadata["expected_days"], 3)
        self.assertEqual(observation.metadata["available_days"], 3)
        self.assertEqual(observation.metadata["missing_days"], 0)
        self.assertEqual(observation.metadata["coverage_fraction"], 1.0)
        self.assertEqual(observation.metadata["aggregation"], "sum")

    def test_missing_days_above_threshold_marks_incomplete_period_degraded(self) -> None:
        result = summarize_rainfall_daily_values(
            [2.0, None, 3.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-03T00:00:00Z",
            is_simulated=True,
        )
        observation = compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            adapter=FakeRainfallAdapter(result),
            config=RainfallCollectionConfig(max_missing_days=0),
        )

        self.assertEqual(observation.value, 5.0)
        self.assertEqual(observation.quality_flag, "degraded")
        self.assertTrue(observation.metadata["incomplete_period"])
        self.assertEqual(observation.metadata["missing_days"], 1)

    def test_missing_days_within_threshold_keeps_ok_quality(self) -> None:
        result = summarize_rainfall_daily_values(
            [2.0, None, 3.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-03T00:00:00Z",
        )
        observation = compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            adapter=FakeRainfallAdapter(result),
            config=RainfallCollectionConfig(max_missing_days=1),
        )

        self.assertEqual(observation.quality_flag, "ok")
        self.assertFalse(observation.metadata["incomplete_period"])

    def test_no_valid_data_returns_no_data_not_zero(self) -> None:
        result = summarize_rainfall_daily_values(
            [None, None],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-02T00:00:00Z",
            valid_pixel_count=0,
            total_pixel_count=4,
        )
        observation = compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-02T00:00:00Z",
            adapter=FakeRainfallAdapter(result),
        )

        self.assertIsNone(observation.value)
        self.assertEqual(observation.quality_flag, "no_data")
        self.assertEqual(observation.metadata["available_days"], 0)

    def test_dates_are_interpreted_in_utc_for_expected_days(self) -> None:
        result = summarize_rainfall_daily_values(
            [1.0, 2.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-02T00:00:00Z",
        )
        observation = compute_current_rainfall(
            "ken",
            "2026-07-01T03:00:00+03:00",
            "2026-07-02T03:00:00+03:00",
            adapter=FakeRainfallAdapter(result),
        )

        self.assertEqual(observation.metadata["expected_days"], 2)

    def test_rejects_adapter_period_mismatch_to_avoid_mixed_accumulations(self) -> None:
        result = summarize_rainfall_daily_values(
            [1.0],
            period_start="2026-07-02T00:00:00Z",
            period_end="2026-07-02T00:00:00Z",
        )
        with self.assertRaisesRegex(RainfallProcessingError, "period"):
            compute_current_rainfall(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-01T00:00:00Z",
                adapter=FakeRainfallAdapter(result),
            )

    def test_collection_can_be_changed_by_argument_and_environment(self) -> None:
        result = summarize_rainfall_daily_values(
            [1.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-01T00:00:00Z",
        )
        explicit = compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-01T00:00:00Z",
            adapter=FakeRainfallAdapter(result),
            config=RainfallCollectionConfig(collection_id="CUSTOM/RAIN"),
        )
        self.assertEqual(explicit.source, "CUSTOM/RAIN")

        with patch.dict(os.environ, {"MWANGAZA_RAINFALL_COLLECTION": "ENV/RAIN"}, clear=True):
            env_config = RainfallCollectionConfig.from_settings()
        self.assertEqual(env_config.collection_id, "ENV/RAIN")

    def test_adapter_receives_region_geometry_and_requested_dates(self) -> None:
        result = summarize_rainfall_daily_values(
            [1.0],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-01T00:00:00Z",
        )
        adapter = FakeRainfallAdapter(result)
        compute_current_rainfall(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-01T00:00:00Z",
            adapter=adapter,
        )
        geometry, start, end, _config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(start, "2026-07-01T00:00:00Z")
        self.assertEqual(end, "2026-07-01T00:00:00Z")

    def test_rejects_invalid_inputs_and_counts(self) -> None:
        with self.assertRaisesRegex(RainfallProcessingError, "period_start"):
            compute_current_rainfall(
                "ken",
                "2026-07-02T00:00:00Z",
                "2026-07-01T00:00:00Z",
                adapter=FakeRainfallAdapter(
                    RainfallQueryResult(
                        accumulated_mm=1.0,
                        available_days=1,
                        actual_period_start="2026-07-02T00:00:00Z",
                        actual_period_end="2026-07-01T00:00:00Z",
                    )
                ),
            )

        with self.assertRaisesRegex(RainfallProcessingError, "non-negative"):
            summarize_rainfall_daily_values(
                [-1.0],
                period_start="2026-07-01T00:00:00Z",
                period_end="2026-07-01T00:00:00Z",
            )

        bad_count = RainfallQueryResult(
            accumulated_mm=1.0,
            available_days=2,
            actual_period_start="2026-07-01T00:00:00Z",
            actual_period_end="2026-07-01T00:00:00Z",
        )
        with self.assertRaisesRegex(RainfallProcessingError, "available_days"):
            compute_current_rainfall(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-01T00:00:00Z",
                adapter=FakeRainfallAdapter(bad_count),
            )


if __name__ == "__main__":
    unittest.main()

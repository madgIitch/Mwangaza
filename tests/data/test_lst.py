from __future__ import annotations

import unittest

from mwangaza.data.lst import (
    LstCollectionConfig,
    LstProcessingError,
    LstQueryResult,
    compute_current_lst,
    summarize_lst_raw_values,
)
from mwangaza.regions import get_region


class FakeLstAdapter:
    def __init__(self, result: LstQueryResult) -> None:
        self.result = result
        self.calls: list[tuple[dict[str, object], str, str, LstCollectionConfig]] = []

    def query_lst(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: LstCollectionConfig,
    ) -> LstQueryResult:
        self.calls.append((geometry, period_start, period_end, config))
        return self.result


class CurrentLstTests(unittest.TestCase):
    def test_converts_raw_kelvin_scaled_values_to_celsius_observation(self) -> None:
        result = summarize_lst_raw_values(
            [15000, 15500, 16000],
            [True, True, True],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
            is_simulated=True,
        )
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=FakeLstAdapter(result),
        )

        self.assertEqual(observation.indicator, "lst_c")
        self.assertEqual(observation.unit, "celsius")
        self.assertEqual(observation.quality_flag, "ok")
        self.assertAlmostEqual(observation.value or 0.0, 36.85)
        self.assertAlmostEqual(observation.metadata["mean_c"], 36.85)
        self.assertAlmostEqual(observation.metadata["median_c"], 36.85)
        self.assertEqual(observation.metadata["valid_pixel_count"], 3)
        self.assertEqual(observation.metadata["total_pixel_count"], 3)
        self.assertEqual(observation.metadata["coverage_fraction"], 1.0)

    def test_quality_mask_excludes_bad_pixels_from_statistics_and_coverage(self) -> None:
        result = summarize_lst_raw_values(
            [15000, 25000, 16000, None],
            [True, False, True, True],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=FakeLstAdapter(result),
        )

        self.assertAlmostEqual(observation.value or 0.0, 36.85)
        self.assertEqual(observation.metadata["valid_pixel_count"], 2)
        self.assertEqual(observation.metadata["total_pixel_count"], 4)
        self.assertEqual(observation.metadata["quality_masked_pixels"], 2)
        self.assertEqual(observation.metadata["coverage_fraction"], 0.5)

    def test_low_coverage_marks_degraded_without_dropping_value(self) -> None:
        result = summarize_lst_raw_values(
            [15000, None, None, None],
            [True, True, True, True],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=FakeLstAdapter(result),
            config=LstCollectionConfig(min_coverage_fraction=0.5),
        )

        self.assertEqual(observation.quality_flag, "degraded")
        self.assertIsNotNone(observation.value)
        self.assertEqual(observation.metadata["coverage_fraction"], 0.25)

    def test_no_valid_pixels_returns_no_data_not_zero(self) -> None:
        result = summarize_lst_raw_values(
            [15000, 16000],
            [False, False],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=FakeLstAdapter(result),
        )

        self.assertIsNone(observation.value)
        self.assertEqual(observation.quality_flag, "no_data")
        self.assertEqual(observation.metadata["valid_pixel_count"], 0)

    def test_physically_impossible_aggregate_is_invalid(self) -> None:
        result = summarize_lst_raw_values(
            [25000],
            [True],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=FakeLstAdapter(result),
        )

        self.assertIsNone(observation.value)
        self.assertEqual(observation.quality_flag, "invalid")
        self.assertEqual(observation.metadata["invalid_reason"], "mean_c_outside_physical_range")

    def test_rejects_adapter_period_mismatch(self) -> None:
        result = summarize_lst_raw_values(
            [15000],
            [True],
            period_start="2026-07-02T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        with self.assertRaisesRegex(LstProcessingError, "period"):
            compute_current_lst(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=FakeLstAdapter(result),
            )

    def test_adapter_receives_region_geometry_and_config(self) -> None:
        result = summarize_lst_raw_values(
            [15000],
            [True],
            period_start="2026-07-01T00:00:00Z",
            period_end="2026-07-08T00:00:00Z",
        )
        adapter = FakeLstAdapter(result)
        config = LstCollectionConfig(collection_id="CUSTOM/LST", scale=0.01)
        observation = compute_current_lst(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=config,
        )

        geometry, start, end, received_config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(start, "2026-07-01T00:00:00Z")
        self.assertEqual(end, "2026-07-08T00:00:00Z")
        self.assertEqual(received_config, config)
        self.assertEqual(observation.source, "CUSTOM/LST")

    def test_rejects_invalid_inputs_counts_and_config(self) -> None:
        with self.assertRaisesRegex(LstProcessingError, "same length"):
            summarize_lst_raw_values(
                [15000],
                [],
                period_start="2026-07-01T00:00:00Z",
                period_end="2026-07-08T00:00:00Z",
            )
        with self.assertRaisesRegex(LstProcessingError, "scale"):
            summarize_lst_raw_values(
                [15000],
                [True],
                period_start="2026-07-01T00:00:00Z",
                period_end="2026-07-08T00:00:00Z",
                config=LstCollectionConfig(scale=0),
            )
        bad_counts = LstQueryResult(
            mean_c=20.0,
            median_c=20.0,
            valid_pixel_count=2,
            total_pixel_count=1,
            actual_period_start="2026-07-01T00:00:00Z",
            actual_period_end="2026-07-08T00:00:00Z",
        )
        with self.assertRaisesRegex(LstProcessingError, "valid_pixel_count"):
            compute_current_lst(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                adapter=FakeLstAdapter(bad_counts),
            )


if __name__ == "__main__":
    unittest.main()

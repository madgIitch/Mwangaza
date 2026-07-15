from __future__ import annotations

import unittest

from mwangaza.data.rainfall import RainfallCollectionConfig, RainfallQueryResult
from mwangaza.data.rainfall_climatology import (
    RainfallClimatologyConfig,
    RainfallClimatologyError,
    compute_rainfall_climatology,
)
from mwangaza.regions import get_region


class FakeHistoricalRainfallAdapter:
    def __init__(self, results: dict[str, RainfallQueryResult]) -> None:
        self.results = results
        self.calls: list[tuple[dict[str, object], str, str, RainfallCollectionConfig]] = []

    def query_rainfall(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: RainfallCollectionConfig,
    ) -> RainfallQueryResult:
        self.calls.append((geometry, period_start, period_end, config))
        return self.results[period_start[:4]]


def yearly_result(year: int, value: float | None, available_days: int = 3) -> RainfallQueryResult:
    return RainfallQueryResult(
        accumulated_mm=value,
        available_days=available_days,
        actual_period_start=f"{year}-07-01T00:00:00Z",
        actual_period_end=f"{year}-07-03T00:00:00Z",
        valid_pixel_count=0 if value is None else 3,
        total_pixel_count=3,
        is_simulated=True,
    )


class RainfallClimatologyTests(unittest.TestCase):
    def test_computes_distribution_statistics_from_included_years(self) -> None:
        adapter = FakeHistoricalRainfallAdapter(
            {
                "2001": yearly_result(2001, 10.0),
                "2002": yearly_result(2002, 20.0),
                "2003": yearly_result(2003, 100.0),
                "2004": yearly_result(2004, 1000.0),
                "2005": yearly_result(2005, 10000.0),
            }
        )

        baseline = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001, 2002, 2003, 2004, 2005],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=5, collection_id="TEST/RAIN"),
        )

        self.assertEqual(baseline.indicator, "rainfall_mm")
        self.assertEqual(baseline.unit, "mm")
        self.assertEqual(baseline.quality_flag, "ok")
        self.assertAlmostEqual(baseline.mean or 0, 2226.0)
        self.assertAlmostEqual(baseline.median or 0, 100.0)
        self.assertAlmostEqual(baseline.percentile_20 or 0, 18.0)
        self.assertAlmostEqual(baseline.percentile_50 or 0, 100.0)
        self.assertAlmostEqual(baseline.percentile_80 or 0, 2800.0)
        self.assertAlmostEqual(baseline.stddev or 0, 3904.7437816071874)
        self.assertEqual(baseline.included_years, (2001, 2002, 2003, 2004, 2005))
        self.assertEqual(baseline.metadata["collection_id"], "TEST/RAIN")
        self.assertEqual(baseline.metadata["sample_size"], 5)

    def test_excludes_years_below_coverage_threshold(self) -> None:
        adapter = FakeHistoricalRainfallAdapter(
            {
                "2001": yearly_result(2001, 10.0),
                "2002": yearly_result(2002, 20.0, available_days=1),
                "2003": yearly_result(2003, 30.0),
            }
        )

        baseline = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001, 2002, 2003],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=2, min_coverage_fraction=0.8),
        )

        self.assertEqual(baseline.included_years, (2001, 2003))
        self.assertEqual(baseline.mean, 20.0)
        self.assertEqual(baseline.excluded_years[0]["year"], 2002)
        self.assertEqual(baseline.excluded_years[0]["reason"], "insufficient_coverage")

    def test_insufficient_history_preserves_exclusions_and_uses_none_statistics(self) -> None:
        adapter = FakeHistoricalRainfallAdapter(
            {
                "2001": yearly_result(2001, 10.0),
                "2002": yearly_result(2002, None, available_days=0),
                "2003": yearly_result(2003, 30.0),
            }
        )

        baseline = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001, 2002, 2003],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=3),
        )

        self.assertEqual(baseline.quality_flag, "insufficient_history")
        self.assertIsNone(baseline.mean)
        self.assertIsNone(baseline.median)
        self.assertIsNone(baseline.stddev)
        self.assertIsNone(baseline.percentile_20)
        self.assertEqual(baseline.included_years, (2001, 2003))
        self.assertEqual(baseline.excluded_years[0], {"year": 2002, "reason": "no_data"})

    def test_baseline_version_changes_with_source_window_and_included_years(self) -> None:
        adapter = FakeHistoricalRainfallAdapter(
            {
                "2001": yearly_result(2001, 10.0),
                "2002": yearly_result(2002, 20.0),
            }
        )
        base = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001, 2002],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=2, collection_id="A"),
        )
        changed_source = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001, 2002],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=2, collection_id="B"),
        )
        changed_years = compute_rainfall_climatology(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-03T00:00:00Z",
            years=[2001],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=1, collection_id="A"),
        )

        self.assertNotEqual(base.baseline_version, changed_source.baseline_version)
        self.assertNotEqual(base.baseline_version, changed_years.baseline_version)

    def test_utc_equivalent_windows_and_adapter_period_mismatch(self) -> None:
        adapter = FakeHistoricalRainfallAdapter({"2001": yearly_result(2001, 10.0)})
        compute_rainfall_climatology(
            "ken",
            "2026-07-01T03:00:00+03:00",
            "2026-07-03T03:00:00+03:00",
            years=[2001],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=1),
        )
        geometry, start, end, _config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(start, "2001-07-01T00:00:00Z")
        self.assertEqual(end, "2001-07-03T00:00:00Z")

        mismatch = FakeHistoricalRainfallAdapter(
            {
                "2001": RainfallQueryResult(
                    accumulated_mm=10.0,
                    available_days=3,
                    actual_period_start="2001-07-02T00:00:00Z",
                    actual_period_end="2001-07-03T00:00:00Z",
                )
            }
        )
        with self.assertRaisesRegex(RainfallClimatologyError, "period"):
            compute_rainfall_climatology(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-03T00:00:00Z",
                years=[2001],
                adapter=mismatch,
                config=RainfallClimatologyConfig(min_years=1),
            )

    def test_leap_day_omits_non_leap_historical_years(self) -> None:
        adapter = FakeHistoricalRainfallAdapter(
            {
                "2000": RainfallQueryResult(
                    accumulated_mm=12.0,
                    available_days=1,
                    actual_period_start="2000-02-29T00:00:00Z",
                    actual_period_end="2000-02-29T00:00:00Z",
                )
            }
        )

        baseline = compute_rainfall_climatology(
            "ken",
            "2024-02-29T00:00:00Z",
            "2024-02-29T00:00:00Z",
            years=[2000, 2001],
            adapter=adapter,
            config=RainfallClimatologyConfig(min_years=1),
        )

        self.assertEqual(baseline.included_years, (2000,))
        self.assertEqual(baseline.excluded_years[0], {"year": 2001, "reason": "invalid_equivalent_window"})

    def test_rejects_invalid_config_and_values(self) -> None:
        adapter = FakeHistoricalRainfallAdapter({"2001": yearly_result(2001, -1.0)})
        with self.assertRaisesRegex(RainfallClimatologyError, "non-negative"):
            compute_rainfall_climatology(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-03T00:00:00Z",
                years=[2001],
                adapter=adapter,
                config=RainfallClimatologyConfig(min_years=1),
            )

        with self.assertRaisesRegex(RainfallClimatologyError, "min_years"):
            compute_rainfall_climatology(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-03T00:00:00Z",
                years=[2001],
                adapter=adapter,
                config=RainfallClimatologyConfig(min_years=0),
            )


if __name__ == "__main__":
    unittest.main()

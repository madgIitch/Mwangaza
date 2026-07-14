from __future__ import annotations

import unittest

from mwangaza.data.climatology import (
    ClimatologyConfig,
    ClimatologyError,
    ClimatologyYearObservation,
    compute_ndvi_climatology,
)
from mwangaza.regions import get_region


class FakeClimatologyAdapter:
    def __init__(self, values: dict[int, float | None]) -> None:
        self.values = values
        self.calls: list[tuple[dict[str, object], int, str, str, ClimatologyConfig]] = []

    def query_ndvi_year(
        self,
        geometry: dict[str, object],
        year: int,
        season_start: str,
        season_end: str,
        config: ClimatologyConfig,
    ) -> ClimatologyYearObservation:
        self.calls.append((geometry, year, season_start, season_end, config))
        value = self.values.get(year)
        return ClimatologyYearObservation(
            year=year,
            value=value,
            quality_flag="ok" if value is not None else "no_data",
        )


class NdviClimatologyTests(unittest.TestCase):
    def test_computes_baseline_statistics_from_configured_years(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 0.4, 2002: 0.5, 2003: 0.6})
        result = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2003, min_years=3, collection_id="TEST/NDVI"),
        )

        self.assertEqual(result.indicator, "ndvi")
        self.assertEqual(result.unit, "index")
        self.assertEqual(result.quality_flag, "ok")
        self.assertAlmostEqual(result.mean or 0, 0.5)
        self.assertAlmostEqual(result.median or 0, 0.5)
        self.assertAlmostEqual(result.stddev or 0, 0.08164965809277258)
        self.assertEqual(result.observations, 3)
        self.assertEqual(result.metadata["effective_years"], [2001, 2002, 2003])
        self.assertEqual(result.metadata["collection_id"], "TEST/NDVI")

    def test_current_year_is_excluded_from_baseline(self) -> None:
        adapter = FakeClimatologyAdapter({2024: 0.4, 2025: 0.6, 2026: 0.9})
        result = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2024, 2026, min_years=2),
        )

        self.assertEqual(result.metadata["effective_years"], [2024, 2025])
        self.assertEqual(result.metadata["excluded_years"], [2026])
        self.assertEqual([call[1] for call in adapter.calls], [2024, 2025])

    def test_insufficient_history_returns_quality_flag_without_statistics(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 0.4, 2002: None, 2003: 0.6})
        result = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2003, min_years=3),
        )

        self.assertEqual(result.quality_flag, "insufficient_history")
        self.assertIsNone(result.mean)
        self.assertIsNone(result.median)
        self.assertIsNone(result.stddev)
        self.assertEqual(result.observations, 2)
        self.assertNotEqual(result.quality_flag, "no_data")

    def test_changing_window_season_or_collection_changes_version(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 0.4, 2002: 0.5})
        base = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2, collection_id="A"),
        )
        changed = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-11",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2, collection_id="A"),
        )
        changed_collection = compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2, collection_id="B"),
        )

        self.assertNotEqual(base.metadata["baseline_version"], changed.metadata["baseline_version"])
        self.assertNotEqual(base.metadata["baseline_version"], changed_collection.metadata["baseline_version"])

    def test_cross_year_season_and_month_lengths_are_supported(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 0.4, 2002: 0.5})
        result = compute_ndvi_climatology(
            "ken",
            "12-15",
            "01-15",
            "2026-12-15T00:00:00Z",
            "2027-01-15T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2),
        )
        self.assertEqual(result.period_start, "2001-12-15T00:00:00Z")
        self.assertEqual(result.period_end, "2003-01-15T00:00:00Z")
        self.assertEqual(result.metadata["period_key"], "12-15_01-15")

        feb = compute_ndvi_climatology(
            "ken",
            "02-01",
            "02-28",
            "2026-02-01T00:00:00Z",
            "2026-02-28T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2),
        )
        self.assertEqual(feb.metadata["season_end"], "02-28")

    def test_adapter_receives_region_geometry_and_no_remote_dependency(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 0.4, 2002: 0.5})
        compute_ndvi_climatology(
            "ken",
            "07-01",
            "07-10",
            "2026-07-01T00:00:00Z",
            "2026-07-10T00:00:00Z",
            adapter=adapter,
            config=ClimatologyConfig(2001, 2002, min_years=2),
        )
        geometry, year, season_start, season_end, _config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(year, 2001)
        self.assertEqual(season_start, "07-01")
        self.assertEqual(season_end, "07-10")

    def test_rejects_invalid_config_and_values(self) -> None:
        adapter = FakeClimatologyAdapter({2001: 1.5})
        with self.assertRaisesRegex(ClimatologyError, "inside"):
            compute_ndvi_climatology(
                "ken",
                "07-01",
                "07-10",
                "2026-07-01T00:00:00Z",
                "2026-07-10T00:00:00Z",
                adapter=adapter,
                config=ClimatologyConfig(2001, 2001, min_years=1),
            )

        with self.assertRaisesRegex(ClimatologyError, "inverted"):
            compute_ndvi_climatology(
                "ken",
                "07-01",
                "07-10",
                "2026-07-10T00:00:00Z",
                "2026-07-01T00:00:00Z",
                adapter=adapter,
                config=ClimatologyConfig(2001, 2001, min_years=1),
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from dataclasses import replace

from mwangaza.contracts import Baseline, IndicatorObservation
from mwangaza.data.temperature_anomaly import (
    LstClimatologyConfig,
    LstYearObservation,
    TemperatureAnomalyConfig,
    TemperatureAnomalyError,
    compute_lst_climatology,
    compute_temperature_anomaly,
)
from mwangaza.regions import get_region


class FakeLstClimatologyAdapter:
    def __init__(self, values: dict[int, float | None]) -> None:
        self.values = values
        self.calls: list[tuple[dict[str, object], int, str, str, LstClimatologyConfig]] = []

    def query_lst_year(
        self,
        geometry: dict[str, object],
        year: int,
        season_start: str,
        season_end: str,
        config: LstClimatologyConfig,
    ) -> LstYearObservation:
        self.calls.append((geometry, year, season_start, season_end, config))
        value = self.values.get(year)
        return LstYearObservation(
            year=year,
            mean_c=value,
            median_c=value,
            quality_flag="ok" if value is not None else "no_data",
        )


def _current(**overrides: object) -> IndicatorObservation:
    payload = {
        "region_id": "ken",
        "indicator": "lst_c",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-08T00:00:00Z",
        "value": 42.0,
        "unit": "celsius",
        "source": "TEST/LST",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"observation_id": "lst-current-ken-202607", "product_variant": "day"},
    }
    payload.update(overrides)
    return IndicatorObservation(**payload)


def _baseline(**overrides: object) -> Baseline:
    payload = {
        "region_id": "ken",
        "indicator": "lst_c",
        "period_start": "2001-07-01T00:00:00Z",
        "period_end": "2020-07-08T00:00:00Z",
        "baseline_start_year": 2001,
        "baseline_end_year": 2020,
        "mean": 36.0,
        "median": 36.0,
        "stddev": 3.0,
        "observations": 20,
        "unit": "celsius",
        "source": "TEST/LST",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"baseline_version": "lst-baseline-v1", "product_variant": "day"},
    }
    payload.update(overrides)
    return Baseline(**payload)


class TemperatureAnomalyTests(unittest.TestCase):
    def test_computes_lst_climatology_baseline_statistics(self) -> None:
        adapter = FakeLstClimatologyAdapter({2001: 34.0, 2002: 36.0, 2003: 38.0})
        baseline = compute_lst_climatology(
            "ken",
            "07-01",
            "07-08",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=LstClimatologyConfig(2001, 2003, min_years=3, collection_id="TEST/LST"),
        )

        self.assertEqual(baseline.indicator, "lst_c")
        self.assertEqual(baseline.unit, "celsius")
        self.assertEqual(baseline.quality_flag, "ok")
        self.assertEqual(baseline.mean, 36.0)
        self.assertEqual(baseline.median, 36.0)
        self.assertAlmostEqual(baseline.stddev or 0.0, 1.632993161855452)
        self.assertEqual(baseline.metadata["product_variant"], "day")
        self.assertEqual(baseline.metadata["included_years"], [2001, 2002, 2003])

    def test_insufficient_lst_history_returns_contractual_quality(self) -> None:
        adapter = FakeLstClimatologyAdapter({2001: 34.0, 2002: None, 2003: 38.0})
        baseline = compute_lst_climatology(
            "ken",
            "07-01",
            "07-08",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=LstClimatologyConfig(2001, 2003, min_years=3),
        )

        self.assertEqual(baseline.quality_flag, "insufficient_history")
        self.assertIsNone(baseline.mean)
        self.assertEqual(baseline.observations, 2)
        self.assertEqual(baseline.metadata["excluded_years"], [2002])

    def test_adapter_receives_region_geometry_and_variant(self) -> None:
        adapter = FakeLstClimatologyAdapter({2001: 34.0})
        config = LstClimatologyConfig(2001, 2001, min_years=1, product_variant="night")
        compute_lst_climatology(
            "ken",
            "07-01",
            "07-08",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            adapter=adapter,
            config=config,
        )
        geometry, year, season_start, season_end, received_config = adapter.calls[0]
        self.assertEqual(geometry, get_region("ken").geometry)
        self.assertEqual(year, 2001)
        self.assertEqual(season_start, "07-01")
        self.assertEqual(season_end, "07-08")
        self.assertEqual(received_config.product_variant, "night")

    def test_positive_temperature_anomaly_means_hotter_than_baseline(self) -> None:
        anomaly = compute_temperature_anomaly(_current(value=42.0), _baseline(mean=36.0, stddev=3.0))

        self.assertEqual(anomaly.indicator, "lst_c")
        self.assertEqual(anomaly.unit, "celsius")
        self.assertEqual(anomaly.value, 6.0)
        self.assertGreater(anomaly.value or 0.0, 0.0)
        self.assertEqual(anomaly.metadata["absolute_anomaly_c"], 6.0)
        self.assertEqual(anomaly.metadata["z_score"], 2.0)

    def test_negative_temperature_anomaly_is_cooler_than_baseline(self) -> None:
        anomaly = compute_temperature_anomaly(_current(value=32.0), _baseline(mean=36.0, stddev=2.0))

        self.assertEqual(anomaly.value, -4.0)
        self.assertEqual(anomaly.metadata["z_score"], -2.0)

    def test_zscore_is_omitted_when_stddev_missing_or_too_small(self) -> None:
        missing = compute_temperature_anomaly(_current(), _baseline(stddev=None))
        small = compute_temperature_anomaly(_current(), _baseline(stddev=0.00001), config=TemperatureAnomalyConfig(zscore_epsilon=0.001))

        self.assertIsNone(missing.metadata["z_score"])
        self.assertEqual(missing.metadata["z_score_reason"], "baseline_stddev_missing")
        self.assertIsNone(small.metadata["z_score"])
        self.assertEqual(small.metadata["z_score_reason"], "baseline_stddev_within_epsilon")

    def test_day_and_night_variants_do_not_mix_by_default(self) -> None:
        with self.assertRaisesRegex(TemperatureAnomalyError, "product_variant"):
            compute_temperature_anomaly(
                _current(metadata={"observation_id": "lst-current", "product_variant": "day"}),
                _baseline(metadata={"baseline_version": "lst-baseline-v1", "product_variant": "night"}),
            )

        anomaly = compute_temperature_anomaly(
            _current(metadata={"observation_id": "lst-current", "product_variant": "day"}),
            _baseline(metadata={"baseline_version": "lst-baseline-v1", "product_variant": "night"}),
            config=TemperatureAnomalyConfig(allow_variant_mismatch=True),
        )
        self.assertEqual(anomaly.metadata["product_variant"], "day")

    def test_preserves_traceability_and_product_variant(self) -> None:
        anomaly = compute_temperature_anomaly(_current(), _baseline())

        self.assertEqual(anomaly.baseline_id, "lst-baseline-v1")
        self.assertEqual(anomaly.metadata["current_id"], "lst-current-ken-202607")
        self.assertEqual(anomaly.metadata["baseline_id"], "lst-baseline-v1")
        self.assertEqual(anomaly.metadata["baseline_version"], "lst-baseline-v1")
        self.assertEqual(anomaly.metadata["product_variant"], "day")

    def test_quality_propagates_without_converting_absence_to_zero(self) -> None:
        no_data_current = replace(_current(), value=None, quality_flag="no_data")
        insufficient_baseline = replace(_baseline(), mean=None, median=None, stddev=None, quality_flag="insufficient_history")

        no_data = compute_temperature_anomaly(no_data_current, _baseline())
        insufficient = compute_temperature_anomaly(_current(), insufficient_baseline)
        degraded = compute_temperature_anomaly(replace(_current(), quality_flag="degraded"), _baseline())

        self.assertEqual(no_data.quality_flag, "no_data")
        self.assertIsNone(no_data.value)
        self.assertEqual(no_data.metadata["non_conclusive_reason"], "current_no_data")
        self.assertEqual(insufficient.quality_flag, "insufficient_history")
        self.assertIsNone(insufficient.value)
        self.assertEqual(insufficient.metadata["non_conclusive_reason"], "baseline_insufficient_history")
        self.assertEqual(degraded.quality_flag, "degraded")
        self.assertIsNotNone(degraded.value)

    def test_rejects_incompatible_inputs_and_invalid_values(self) -> None:
        with self.assertRaisesRegex(TemperatureAnomalyError, "lst_c"):
            compute_temperature_anomaly(_current(indicator="ndvi"), _baseline())
        with self.assertRaisesRegex(TemperatureAnomalyError, "celsius"):
            compute_temperature_anomaly(_current(unit="index"), _baseline())
        with self.assertRaisesRegex(TemperatureAnomalyError, "region_id"):
            compute_temperature_anomaly(_current(region_id="som"), _baseline())
        with self.assertRaisesRegex(TemperatureAnomalyError, "physical"):
            compute_temperature_anomaly(_current(value=120.0), _baseline())

    def test_does_not_generate_recommendations_or_scores(self) -> None:
        anomaly = compute_temperature_anomaly(_current(), _baseline())
        serialized = str(anomaly.to_dict()).lower()

        self.assertNotIn("recommendation", serialized)
        self.assertNotIn("action", serialized)
        self.assertNotIn("alert", serialized)
        self.assertNotIn("severity", serialized)
        self.assertNotIn("composite", serialized)


if __name__ == "__main__":
    unittest.main()

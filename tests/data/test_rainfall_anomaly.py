from __future__ import annotations

import unittest
from dataclasses import replace

from mwangaza.contracts import Baseline, IndicatorObservation
from mwangaza.data.rainfall_anomaly import (
    RainfallAnomalyConfig,
    RainfallAnomalyError,
    compute_rainfall_anomaly,
)
from mwangaza.data.rainfall_climatology import HistoricalRainfallYear, RainfallClimatologyBaseline


def _current(**overrides: object) -> IndicatorObservation:
    payload = {
        "region_id": "ken",
        "indicator": "rainfall_mm",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-03T00:00:00Z",
        "value": 80.0,
        "unit": "mm",
        "source": "TEST/RAIN",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"observation_id": "rain-obs-ken-202607"},
    }
    payload.update(overrides)
    return IndicatorObservation(**payload)


def _baseline(**overrides: object) -> Baseline:
    payload = {
        "region_id": "ken",
        "indicator": "rainfall_mm",
        "period_start": "2001-07-01T00:00:00Z",
        "period_end": "2005-07-03T00:00:00Z",
        "baseline_start_year": 2001,
        "baseline_end_year": 2005,
        "mean": 100.0,
        "median": 100.0,
        "stddev": 20.0,
        "observations": 5,
        "unit": "mm",
        "source": "TEST/RAIN",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {
            "baseline_version": "rain-baseline-v1",
            "historical_values": [50.0, 80.0, 100.0, 120.0, 150.0],
        },
    }
    payload.update(overrides)
    return Baseline(**payload)


class RainfallAnomalyTests(unittest.TestCase):
    def test_negative_value_represents_rainfall_deficit_against_mean(self) -> None:
        result = compute_rainfall_anomaly(_current(value=70.0), _baseline(mean=100.0))

        self.assertEqual(result.indicator, "rainfall_mm")
        self.assertEqual(result.unit, "mm")
        self.assertEqual(result.method, "current_minus_mean")
        self.assertEqual(result.value, -30.0)
        self.assertEqual(result.metadata["absolute_anomaly"], -30.0)
        self.assertEqual(result.metadata["percent_anomaly"], -30.0)
        self.assertEqual(result.metadata["classification"], "deficit")

    def test_positive_value_represents_excess_and_percentile_is_bounded(self) -> None:
        result = compute_rainfall_anomaly(_current(value=160.0), _baseline(mean=100.0))

        self.assertEqual(result.value, 60.0)
        self.assertEqual(result.metadata["percent_anomaly"], 60.0)
        self.assertEqual(result.metadata["classification"], "excess")
        self.assertEqual(result.metadata["empirical_percentile"], 100.0)

    def test_exact_thresholds_are_documented_and_inclusive(self) -> None:
        deficit = compute_rainfall_anomaly(_current(value=80.0), _baseline(mean=100.0))
        normal = compute_rainfall_anomaly(_current(value=81.0), _baseline(mean=100.0))
        excess = compute_rainfall_anomaly(_current(value=120.0), _baseline(mean=100.0))

        self.assertEqual(deficit.metadata["deficit_threshold_percent"], -20.0)
        self.assertEqual(deficit.metadata["excess_threshold_percent"], 20.0)
        self.assertEqual(deficit.metadata["classification"], "deficit")
        self.assertEqual(normal.metadata["classification"], "normal")
        self.assertEqual(excess.metadata["classification"], "excess")

    def test_empirical_percentile_uses_less_than_or_equal_count(self) -> None:
        result = compute_rainfall_anomaly(_current(value=80.0), _baseline())

        self.assertEqual(result.metadata["empirical_percentile"], 40.0)
        self.assertGreaterEqual(result.metadata["empirical_percentile"], 0.0)
        self.assertLessEqual(result.metadata["empirical_percentile"], 100.0)

    def test_rainfall_climatology_wrapper_uses_only_included_years_for_percentile(self) -> None:
        wrapped = RainfallClimatologyBaseline(
            baseline=_baseline(mean=100.0, metadata={"baseline_version": "wrapped-v1"}),
            percentile_20=60.0,
            percentile_50=100.0,
            percentile_80=120.0,
            included_years=(2001, 2003),
            excluded_years=({"year": 2002, "reason": "insufficient_coverage"},),
            yearly_observations=(
                HistoricalRainfallYear(2001, "2001-07-01T00:00:00Z", "2001-07-03T00:00:00Z", 50.0, 3, 3, 1.0, "ok"),
                HistoricalRainfallYear(2002, "2002-07-01T00:00:00Z", "2002-07-03T00:00:00Z", 60.0, 3, 1, 0.33, "ok"),
                HistoricalRainfallYear(2003, "2003-07-01T00:00:00Z", "2003-07-03T00:00:00Z", 100.0, 3, 3, 1.0, "ok"),
            ),
        )

        result = compute_rainfall_anomaly(
            _current(value=90.0),
            wrapped,
            config=RainfallAnomalyConfig(min_percentile_observations=2),
        )

        self.assertEqual(result.metadata["empirical_percentile"], 50.0)

    def test_percentile_is_not_invented_below_minimum_observations(self) -> None:
        result = compute_rainfall_anomaly(
            _current(value=80.0),
            _baseline(metadata={"baseline_version": "rain-baseline-v1", "historical_values": [50.0, 100.0]}),
            config=RainfallAnomalyConfig(min_percentile_observations=3),
        )

        self.assertIsNone(result.metadata["empirical_percentile"])
        self.assertEqual(result.metadata["empirical_percentile_reason"], "insufficient_observations")

    def test_percent_anomaly_is_omitted_when_baseline_mean_is_within_epsilon(self) -> None:
        result = compute_rainfall_anomaly(
            _current(value=0.2),
            _baseline(mean=0.00001),
            config=RainfallAnomalyConfig(percent_epsilon=0.001),
        )

        self.assertIsNone(result.metadata["percent_anomaly"])
        self.assertEqual(result.metadata["percent_anomaly_reason"], "baseline_mean_within_epsilon")
        self.assertEqual(result.metadata["classification"], "not_conclusive")

    def test_preserves_current_and_baseline_traceability(self) -> None:
        result = compute_rainfall_anomaly(_current(), _baseline())

        self.assertEqual(result.baseline_id, "rain-baseline-v1")
        self.assertEqual(result.metadata["current_id"], "rain-obs-ken-202607")
        self.assertEqual(result.metadata["baseline_id"], "rain-baseline-v1")

    def test_propagates_quality_without_converting_absence_to_zero(self) -> None:
        no_data_current = replace(_current(), value=None, quality_flag="no_data")
        insufficient_baseline = replace(_baseline(), mean=None, median=None, stddev=None, quality_flag="insufficient_history")

        no_data = compute_rainfall_anomaly(no_data_current, _baseline())
        insufficient = compute_rainfall_anomaly(_current(), insufficient_baseline)
        degraded = compute_rainfall_anomaly(replace(_current(), quality_flag="degraded"), _baseline())

        self.assertEqual(no_data.quality_flag, "no_data")
        self.assertIsNone(no_data.value)
        self.assertEqual(no_data.metadata["non_conclusive_reason"], "current_no_data")
        self.assertEqual(insufficient.quality_flag, "insufficient_history")
        self.assertIsNone(insufficient.value)
        self.assertEqual(insufficient.metadata["non_conclusive_reason"], "baseline_insufficient_history")
        self.assertEqual(degraded.quality_flag, "degraded")
        self.assertIsNotNone(degraded.value)

    def test_rejects_incompatible_inputs_and_invalid_values(self) -> None:
        with self.assertRaisesRegex(RainfallAnomalyError, "rainfall_mm"):
            compute_rainfall_anomaly(_current(indicator="ndvi"), _baseline())
        with self.assertRaisesRegex(RainfallAnomalyError, "mm"):
            compute_rainfall_anomaly(_current(unit="index"), _baseline())
        with self.assertRaisesRegex(RainfallAnomalyError, "region_id"):
            compute_rainfall_anomaly(_current(region_id="som"), _baseline())
        with self.assertRaisesRegex(RainfallAnomalyError, "non-negative"):
            compute_rainfall_anomaly(_current(value=-1.0), _baseline())

    def test_does_not_encode_alert_actions_or_final_severity(self) -> None:
        result = compute_rainfall_anomaly(_current(), _baseline())
        serialized = str(result.to_dict()).lower()

        self.assertNotIn("severity", serialized)
        self.assertNotIn("alert", serialized)
        self.assertNotIn("action", serialized)


if __name__ == "__main__":
    unittest.main()

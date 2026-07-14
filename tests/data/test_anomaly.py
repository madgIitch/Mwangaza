from __future__ import annotations

import unittest
from dataclasses import replace

from mwangaza.contracts import Baseline, IndicatorObservation
from mwangaza.data.anomaly import NdviAnomalyConfig, NdviAnomalyError, compute_ndvi_anomaly


def _current(**overrides: object) -> IndicatorObservation:
    payload = {
        "region_id": "ken",
        "indicator": "ndvi",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-10T00:00:00Z",
        "value": 0.41,
        "unit": "index",
        "source": "TEST/NDVI",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"observation_id": "obs-ken-202607"},
    }
    payload.update(overrides)
    return IndicatorObservation(**payload)


def _baseline(**overrides: object) -> Baseline:
    payload = {
        "region_id": "ken",
        "indicator": "ndvi",
        "period_start": "2001-07-01T00:00:00Z",
        "period_end": "2020-07-10T00:00:00Z",
        "baseline_start_year": 2001,
        "baseline_end_year": 2020,
        "mean": 0.5,
        "median": 0.5,
        "stddev": 0.05,
        "observations": 20,
        "unit": "index",
        "source": "TEST/NDVI",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"baseline_version": "baseline-ken-v1"},
    }
    payload.update(overrides)
    return Baseline(**payload)


class NdviAnomalyTests(unittest.TestCase):
    def test_computes_absolute_percent_and_zscore_anomaly(self) -> None:
        result = compute_ndvi_anomaly(_current(), _baseline())

        self.assertEqual(result.indicator, "ndvi")
        self.assertEqual(result.unit, "index")
        self.assertEqual(result.method, "current_minus_mean")
        self.assertAlmostEqual(result.value or 0.0, -0.09)
        self.assertAlmostEqual(result.metadata["absolute_anomaly"], -0.09)
        self.assertAlmostEqual(result.metadata["percent_anomaly"], -18.0)
        self.assertAlmostEqual(result.metadata["z_score"], -1.8)

    def test_negative_absolute_anomaly_means_lower_vegetation_than_baseline(self) -> None:
        result = compute_ndvi_anomaly(_current(value=0.2), _baseline(mean=0.45))

        self.assertLess(result.value or 0.0, 0.0)
        self.assertEqual(result.metadata["current_value"], 0.2)
        self.assertEqual(result.metadata["baseline_mean"], 0.45)

    def test_percent_anomaly_is_omitted_when_baseline_mean_is_within_epsilon(self) -> None:
        result = compute_ndvi_anomaly(
            _current(value=0.02),
            _baseline(mean=0.00001),
            config=NdviAnomalyConfig(percent_epsilon=0.001),
        )

        self.assertIsNone(result.metadata["percent_anomaly"])
        self.assertEqual(result.metadata["percent_anomaly_reason"], "baseline_mean_within_epsilon")

    def test_zscore_is_omitted_when_stddev_is_missing_or_too_small(self) -> None:
        missing = compute_ndvi_anomaly(_current(), _baseline(stddev=None))
        small = compute_ndvi_anomaly(_current(), _baseline(stddev=0.00001), config=NdviAnomalyConfig(zscore_epsilon=0.001))

        self.assertIsNone(missing.metadata["z_score"])
        self.assertEqual(missing.metadata["z_score_reason"], "baseline_stddev_missing")
        self.assertIsNone(small.metadata["z_score"])
        self.assertEqual(small.metadata["z_score_reason"], "baseline_stddev_within_epsilon")

    def test_preserves_current_and_baseline_traceability(self) -> None:
        result = compute_ndvi_anomaly(_current(), _baseline())

        self.assertEqual(result.baseline_id, "baseline-ken-v1")
        self.assertEqual(result.metadata["current_id"], "obs-ken-202607")
        self.assertEqual(result.metadata["baseline_id"], "baseline-ken-v1")

    def test_propagates_most_restrictive_quality_without_conclusive_value(self) -> None:
        no_data_current = replace(_current(), value=None, quality_flag="no_data")
        insufficient_baseline = replace(_baseline(), mean=None, median=None, stddev=None, quality_flag="insufficient_history")

        no_data = compute_ndvi_anomaly(no_data_current, _baseline())
        insufficient = compute_ndvi_anomaly(_current(), insufficient_baseline)
        degraded = compute_ndvi_anomaly(replace(_current(), quality_flag="degraded"), _baseline())

        self.assertEqual(no_data.quality_flag, "no_data")
        self.assertIsNone(no_data.value)
        self.assertEqual(insufficient.quality_flag, "insufficient_history")
        self.assertIsNone(insufficient.value)
        self.assertEqual(degraded.quality_flag, "degraded")
        self.assertIsNotNone(degraded.value)

    def test_rejects_incompatible_indicator_unit_or_region(self) -> None:
        with self.assertRaisesRegex(NdviAnomalyError, "ndvi"):
            compute_ndvi_anomaly(_current(indicator="rainfall_mm"), _baseline())
        with self.assertRaisesRegex(NdviAnomalyError, "index"):
            compute_ndvi_anomaly(_current(unit="mm"), _baseline())
        with self.assertRaisesRegex(NdviAnomalyError, "region_id"):
            compute_ndvi_anomaly(_current(region_id="som"), _baseline())

    def test_rejects_invalid_config_and_non_finite_values(self) -> None:
        with self.assertRaisesRegex(NdviAnomalyError, "percent_epsilon"):
            compute_ndvi_anomaly(_current(), _baseline(), config=NdviAnomalyConfig(percent_epsilon=0))
        with self.assertRaisesRegex(NdviAnomalyError, "inside"):
            compute_ndvi_anomaly(_current(value=1.5), _baseline())

    def test_does_not_encode_alert_thresholds_or_severity(self) -> None:
        result = compute_ndvi_anomaly(_current(), _baseline())
        serialized = str(result.to_dict()).lower()

        self.assertNotIn("severity", serialized)
        self.assertNotIn("alert", serialized)
        self.assertNotIn("threshold", serialized)


if __name__ == "__main__":
    unittest.main()

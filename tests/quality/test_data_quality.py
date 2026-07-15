from __future__ import annotations

import unittest
from datetime import UTC, datetime

from mwangaza.contracts import IndicatorObservation
from mwangaza.data.indicator_snapshot import build_indicator_snapshot
from mwangaza.quality import DataQualityError, DataQualityRules, evaluate_data_quality


def _obs(indicator: str, unit: str, quality: str = "ok", coverage: float = 1.0):
    return IndicatorObservation(
        region_id="ken",
        indicator=indicator,
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-08T00:00:00Z",
        value=None if quality in {"no_data", "insufficient_history", "invalid"} else 1.0,
        unit=unit,
        source=f"TEST/{indicator}",
        quality_flag=quality,
        is_simulated=True,
        metadata={"updated_at": "2026-07-09T00:00:00Z", "coverage_fraction": coverage},
    )


class DataQualityTests(unittest.TestCase):
    def test_complete_snapshot_scores_high_with_breakdown(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index"), _obs("rainfall_mm", "mm"), _obs("lst_c", "celsius")],
        )
        report = evaluate_data_quality(
            snapshot,
            now=datetime(2026, 7, 9, 12, tzinfo=UTC),
        )

        self.assertGreaterEqual(report.score, 80)
        self.assertEqual(report.status, "ok")
        self.assertFalse(report.blocks_automatic_alerts)
        self.assertEqual(report.contributions["spatial_coverage"], 100)

    def test_degraded_snapshot_keeps_available_data_and_warns(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index"), _obs("rainfall_mm", "mm", quality="degraded", coverage=0.4)],
        )
        report = evaluate_data_quality(snapshot, now=datetime(2026, 7, 9, 12, tzinfo=UTC))

        self.assertIn("rainfall_mm", report.available_indicators)
        self.assertIn("degraded_indicators", report.warnings)
        self.assertIn(report.status, {"degraded", "data_review_required"})

    def test_blocked_quality_requires_data_review(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index")],
            expected_indicators=("ndvi", "rainfall_mm", "lst_c"),
        )
        report = evaluate_data_quality(snapshot, now=datetime(2026, 7, 20, tzinfo=UTC))

        self.assertLess(report.score, 50)
        self.assertEqual(report.status, "data_review_required")
        self.assertTrue(report.blocks_automatic_alerts)
        self.assertIn("missing_indicators", report.warnings)
        self.assertIn("stale_data", report.warnings)

    def test_rules_are_versioned_and_configurable(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index")],
        )
        report = evaluate_data_quality(
            snapshot,
            DataQualityRules(rules_version="custom-v2", critical_threshold=10),
            now=datetime(2026, 7, 9, tzinfo=UTC),
        )

        self.assertEqual(report.rules_version, "custom-v2")
        self.assertEqual(report.status, "ok")

    def test_rejects_invalid_coverage(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index", coverage=1.2)],
        )
        with self.assertRaisesRegex(DataQualityError, "coverage_fraction"):
            evaluate_data_quality(snapshot)


if __name__ == "__main__":
    unittest.main()

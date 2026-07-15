from __future__ import annotations

import unittest
from datetime import UTC, datetime

from mwangaza.contracts import IndicatorObservation
from mwangaza.data.indicator_snapshot import build_indicator_snapshot
from mwangaza.quality import DataQualityRules, evaluate_data_quality
from mwangaza.risk import RiskModelConfig, RiskScoreError, compute_composite_drought_score


def _obs(indicator: str, unit: str, value: float):
    return IndicatorObservation(
        region_id="ken",
        indicator=indicator,
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-08T00:00:00Z",
        value=value,
        unit=unit,
        source=f"TEST/{indicator}",
        quality_flag="ok",
        is_simulated=True,
        metadata={"updated_at": "2026-07-09T00:00:00Z"},
    )


def _quality(snapshot):
    return evaluate_data_quality(
        snapshot,
        DataQualityRules(critical_threshold=10),
        now=datetime(2026, 7, 9, tzinfo=UTC),
    )


class CompositeDroughtScoreTests(unittest.TestCase):
    def test_score_between_zero_and_hundred_with_contributions(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index", 0.3), _obs("rainfall_mm", "mm", 30), _obs("lst_c", "celsius", 35)],
        )
        risk = compute_composite_drought_score(snapshot, _quality(snapshot))

        self.assertIsNotNone(risk.composite_score)
        self.assertGreaterEqual(risk.composite_score or 0, 0)
        self.assertLessEqual(risk.composite_score or 0, 100)
        self.assertEqual(set(risk.metadata["contributions"]), {"ndvi", "rainfall_mm", "lst_c"})
        self.assertEqual(risk.metadata["model_version"], "composite-risk-v1")

    def test_missing_optional_renormalizes_weights(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index", 0.3), _obs("rainfall_mm", "mm", 30)],
        )
        risk = compute_composite_drought_score(snapshot, _quality(snapshot))

        self.assertEqual(risk.metadata["missing_optional"], ["lst_c"])
        self.assertAlmostEqual(sum(risk.metadata["renormalized_weights"].values()), 1.0)

    def test_missing_required_or_blocked_quality_returns_unknown_override(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index", 0.3)],
        )
        risk = compute_composite_drought_score(snapshot, _quality(snapshot))

        self.assertIsNone(risk.composite_score)
        self.assertEqual(risk.metadata["risk_level_override"], "unknown")
        self.assertEqual(risk.metadata["missing_required"], ["rainfall_mm"])

    def test_same_snapshot_and_version_are_deterministic(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("rainfall_mm", "mm", 30), _obs("ndvi", "index", 0.3)],
        )
        first = compute_composite_drought_score(snapshot, _quality(snapshot))
        second = compute_composite_drought_score(snapshot, _quality(snapshot))

        self.assertEqual(first.to_dict(), second.to_dict())

    def test_invalid_weights_fail(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_obs("ndvi", "index", 0.3), _obs("rainfall_mm", "mm", 30)],
        )
        with self.assertRaisesRegex(RiskScoreError, "sum"):
            compute_composite_drought_score(
                snapshot,
                _quality(snapshot),
                RiskModelConfig(weights={"ndvi": 0.5, "rainfall_mm": 0.6}),
            )


if __name__ == "__main__":
    unittest.main()

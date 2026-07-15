from __future__ import annotations

import unittest
from dataclasses import replace

from mwangaza.actions import (
    ActionCatalog,
    ActionTemplate,
    RecommendationError,
    default_action_catalog,
    recommend_actions,
)
from mwangaza.contracts import RiskSnapshot


def _risk(level: str, score: float | None = 20.0) -> RiskSnapshot:
    return RiskSnapshot(
        region_id="ken",
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-08T00:00:00Z",
        composite_score=score,
        risk_level=level,
        contributing_indicators=("ndvi",),
        source="TEST/RISK",
        quality_flag="ok" if score is not None else "invalid",
        is_simulated=True,
        metadata={},
    )


class RecommendationTests(unittest.TestCase):
    def test_recommendations_include_required_fields_and_disclaimer(self) -> None:
        recommendation = recommend_actions(_risk("watch"))[0]

        self.assertTrue(recommendation.action)
        self.assertTrue(recommendation.suggested_actor)
        self.assertEqual(recommendation.urgency, "preparation")
        self.assertEqual(recommendation.evidence["risk_level"], "watch")
        self.assertEqual(recommendation.recommendation_version, "actions-v1")
        self.assertIn("not an official order", recommendation.disclaimer)
        self.assertIn("medical advice", recommendation.disclaimer)

    def test_levels_map_to_expected_urgency(self) -> None:
        cases = {
            "low": "monitoring",
            "watch": "preparation",
            "warning": "prepositioning",
            "emergency": "urgent_activation",
        }
        risk_map = {"low": "green", "watch": "watch", "warning": "warning", "emergency": "emergency"}
        for risk_level, expected_urgency in cases.items():
            risk = _risk(risk_level)
            if risk_level == "low":
                risk = replace(risk, metadata={"risk_level_override": risk_map[risk_level]})
            self.assertEqual(recommend_actions(risk)[0].urgency, expected_urgency)

    def test_unreliable_score_recommends_data_review(self) -> None:
        recommendation = recommend_actions(_risk("low", score=None))[0]

        self.assertEqual(recommendation.urgency, "data_review")
        self.assertIn("Review data quality", recommendation.action)

    def test_catalog_is_editable_without_code_change(self) -> None:
        catalog = default_action_catalog()
        custom = ActionCatalog(
            "custom-actions-v2",
            {**catalog.templates, "watch": ActionTemplate("watch", "Custom prepare", "Custom actor", "custom")},
        )
        recommendation = recommend_actions(_risk("watch"), custom)[0]

        self.assertEqual(recommendation.action, "Custom prepare")
        self.assertEqual(recommendation.recommendation_version, "custom-actions-v2")

    def test_incomplete_catalog_fails(self) -> None:
        with self.assertRaisesRegex(RecommendationError, "missing"):
            recommend_actions(_risk("watch"), ActionCatalog("bad", {}))


if __name__ == "__main__":
    unittest.main()

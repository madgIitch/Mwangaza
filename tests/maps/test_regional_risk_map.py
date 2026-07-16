from __future__ import annotations

import unittest

from mwangaza.contracts import RiskSnapshot
from mwangaza.maps import (
    RISK_COLOR_LEVELS,
    build_regional_risk_map,
    build_regional_risk_map_html,
    risk_level_to_color,
)
from mwangaza.regions import COUNTRY_LEVEL, list_regions
from smoke_tests.sprint23_regional_risk_map_real_gee import find_sensitive_content


class RegionalRiskMapTests(unittest.TestCase):
    def test_risk_levels_map_to_required_color_levels(self) -> None:
        self.assertEqual(RISK_COLOR_LEVELS, ("green", "yellow", "orange", "red", "unknown"))
        self.assertEqual(risk_level_to_color("low", 12.0, "ok"), "green")
        self.assertEqual(risk_level_to_color("watch", 38.0, "ok"), "yellow")
        self.assertEqual(risk_level_to_color("warning", 62.0, "ok"), "orange")
        self.assertEqual(risk_level_to_color("emergency", 82.0, "ok"), "red")
        self.assertEqual(risk_level_to_color("low", None, "no_data"), "unknown")

    def test_missing_snapshot_is_unknown_not_green(self) -> None:
        risk_map = build_regional_risk_map([_risk("ken", 82.0, "emergency")])
        by_id = {region.region_id: region for region in risk_map.regions}

        self.assertEqual(by_id["ken"].color_level, "red")
        self.assertEqual(by_id["som"].color_level, "unknown")
        self.assertNotEqual(by_id["som"].color_level, "green")

    def test_map_uses_ui_geometry_and_tooltip_contract(self) -> None:
        countries = list_regions(level=COUNTRY_LEVEL, include_pilots=False)
        risk_map = build_regional_risk_map(
            [_risk("som", 55.0, "warning")],
            selected_region_id="som",
            regions=countries,
        )
        somalia_region = next(region for region in countries if region.id == "som")
        somalia_map_region = next(region for region in risk_map.regions if region.region_id == "som")

        self.assertEqual(somalia_map_region.ui_geometry, somalia_region.ui_geometry)
        self.assertNotEqual(somalia_map_region.ui_geometry, somalia_region.geometry)
        self.assertIn("Somalia", somalia_map_region.tooltip)
        self.assertIn("score: 55", somalia_map_region.tooltip)
        self.assertIn("level: orange", somalia_map_region.tooltip)
        self.assertIn("quality: ok", somalia_map_region.tooltip)

    def test_html_renders_legend_selection_and_region_paths(self) -> None:
        html = build_regional_risk_map_html(
            build_regional_risk_map([_risk("som", 82.0, "emergency")], selected_region_id="som")
        )

        for level in RISK_COLOR_LEVELS:
            self.assertIn(f'data-risk-level="{level}"', html)
        self.assertIn('data-selected-region="som"', html)
        self.assertIn('data-region-id="som"', html)
        self.assertIn("risk-region risk-red is-selected", html)
        self.assertIn("<title>Somalia | score: 82 | level: red", html)

    def test_smoke_payload_validator_rejects_sensitive_fields(self) -> None:
        findings = find_sensitive_content({"metadata": {"private_key": "redacted"}})

        self.assertEqual(findings, ["$.metadata.private_key"])


def _risk(region_id: str, score: float | None, risk_level: str) -> RiskSnapshot:
    return RiskSnapshot(
        region_id=region_id,
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-15T00:00:00Z",
        composite_score=score,
        risk_level=risk_level,
        contributing_indicators=("ndvi", "rainfall_mm") if score is not None else (),
        source="mwangaza.risk.composite",
        quality_flag="ok" if score is not None else "no_data",
        is_simulated=True,
        metadata={"model_version": "test"},
    )


if __name__ == "__main__":
    unittest.main()

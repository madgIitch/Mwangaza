from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mwangaza.alerts.repository import AlertRepository
from mwangaza.actions import recommend_actions
from mwangaza.contracts import RiskSnapshot
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import SAFE_ERROR_MESSAGE, build_dashboard_shell_html, render_dashboard


class FakeStreamlit:
    def __init__(self) -> None:
        self.page_config: dict[str, object] | None = None
        self.markdown_calls: list[tuple[str, bool]] = []
        self.html_calls: list[str] = []

    def set_page_config(self, **kwargs: object) -> None:
        self.page_config = kwargs

    def markdown(self, body: str, *, unsafe_allow_html: bool = False) -> None:
        self.markdown_calls.append((body, unsafe_allow_html))

    def html(self, body: str) -> None:
        self.html_calls.append(body)


class FakeComponentsV1:
    def __init__(self) -> None:
        self.html_calls: list[tuple[str, int, bool]] = []

    def html(self, body: str, *, height: int, scrolling: bool) -> None:
        self.html_calls.append((body, height, scrolling))


class FakeComponents:
    def __init__(self) -> None:
        self.v1 = FakeComponentsV1()


class FakeStreamlitWithComponents(FakeStreamlit):
    def __init__(self) -> None:
        super().__init__()
        self.components = FakeComponents()


class DashboardShellTests(unittest.TestCase):
    def test_home_shell_shows_brand_update_and_data_status(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Mwangaza", html)
        self.assertIn("Bringing Light to Early Action", html)
        self.assertIn("Last update:", html)
        self.assertIn("Data is current", html)

    def test_navigation_contains_required_sections(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        for label in ("Overview", "Region", "Alerts", "Reports", "About"):
            self.assertIn(f">{label}<", html)

    def test_data_modes_are_visually_distinct(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("cache"))

        self.assertIn('data-mode="live"', html)
        self.assertIn(">Live data<", html)
        self.assertIn('data-mode="cache"', html)
        self.assertIn(">Cache data<", html)
        self.assertIn('data-mode="demo"', html)
        self.assertIn(">Demo data<", html)
        self.assertIn('mode-chip is-active" data-mode="cache"', html)

    def test_materialized_cache_feeds_dashboard_before_demo_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            risk = _risk_snapshot(is_simulated=False).to_dict()
            ndvi = {
                "payload_type": "indicator_observation",
                "schema_version": "mwangaza.contracts.v1",
                "region_id": "ken",
                "indicator": "ndvi",
                "period_start": "2026-07-01T00:00:00Z",
                "period_end": "2026-07-08T00:00:00Z",
                "value": 0.31,
                "unit": "index",
                "source": "MODIS/061/MOD13Q1",
                "quality_flag": "ok",
                "is_simulated": False,
                "metadata": {"updated_at": "2026-07-09T00:00:00Z"},
            }
            (cache_dir / "risk.json").write_text(json.dumps({"payload": risk}), encoding="utf-8")
            (cache_dir / "ndvi.json").write_text(json.dumps({"payload": ndvi}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        self.assertEqual(data.data_status.mode, "cache")
        self.assertEqual(data.data_status.source, "Materialized observed data")
        self.assertEqual(data.selected_region, "KEN")
        self.assertEqual(data.risk_map.selected_region_id, "ken")
        self.assertEqual(
            next(region for region in data.risk_map.regions if region.region_id == "ken").color_level,
            "red",
        )
        self.assertIn("0.31", {metric.value for metric in data.metrics})
        self.assertIn("Activate urgent coordination review", data.recommendations[0])

    def test_default_loader_uses_live_gee_payloads_before_cache_or_demo(self) -> None:
        with patch(
            "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
            return_value=[_risk_snapshot(is_simulated=False).to_dict()],
        ):
            data = load_dashboard_shell_data()

        self.assertEqual(data.data_status.mode, "live")
        self.assertEqual(data.data_status.source, "Google Earth Engine live query")
        self.assertEqual(data.data_status.message, "Using live Google Earth Engine data")
        self.assertEqual(data.selected_region, "KEN")

    def test_default_loader_keeps_preferred_live_region_with_multiple_risks(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_DASHBOARD_REGION_ID": "som"}),
            patch(
                "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
                return_value=[
                    _json_payload(
                        _risk_snapshot(region_id="som", risk_level="watch", score=49.8, is_simulated=False)
                    ),
                    _json_payload(
                        _risk_snapshot(region_id="ken", risk_level="emergency", score=82.0, is_simulated=False)
                    ),
                ],
            ),
        ):
            data = load_dashboard_shell_data()

        self.assertEqual(data.selected_region, "SOM")
        self.assertEqual(data.risk_map.selected_region_id, "som")
        by_region = {region.region_id: region for region in data.risk_map.regions}
        self.assertEqual(by_region["som"].color_level, "yellow")
        self.assertEqual(by_region["ken"].color_level, "red")
        self.assertIn("49.8", {metric.value for metric in data.metrics})

    def test_dashboard_debug_flag_logs_loader_decision(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_DASHBOARD_DEBUG": "1"}),
            patch(
                "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
                return_value=[_risk_snapshot(is_simulated=False).to_dict()],
            ),
            patch("builtins.print") as fake_print,
        ):
            load_dashboard_shell_data()

        lines = [call.args[0] for call in fake_print.call_args_list]
        self.assertIn("[mwangaza.dashboard] trying live GEE dashboard payloads", lines)
        self.assertIn(
            "[mwangaza.dashboard] loader selected mode=live source=Google Earth Engine live query",
            lines,
        )

    def test_dashboard_renders_regional_risk_map_with_legend_and_tooltips(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('class="regional-risk-map"', html)
        self.assertIn('aria-label="IGAD regional risk map"', html)
        for level in ("green", "yellow", "orange", "red", "unknown"):
            self.assertIn(f'data-risk-level="{level}"', html)
        self.assertIn("Somalia | score: 82 | level: red", html)
        self.assertIn("risk-region risk-red is-selected", html)

    def test_materialized_cache_accepts_powershell_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            body = json.dumps({"payload": _risk_snapshot(is_simulated=False).to_dict()})
            (cache_dir / "risk.json").write_text(f"\ufeff{body}", encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        self.assertEqual(data.data_status.mode, "cache")
        self.assertEqual(data.selected_region, "KEN")

    def test_alert_sqlite_overrides_demo_alert_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            risk = _risk_snapshot(risk_level="warning", score=66.0, is_simulated=False)
            (cache_dir / "risk.json").write_text(
                json.dumps({"payload": risk.to_dict()}),
                encoding="utf-8",
            )
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                repo.upsert_alert(risk, recommend_actions(risk))
            finally:
                repo.close()

            data = load_dashboard_shell_data(
                cache_dir=cache_dir,
                data_dir=Path(tmp),
                alert_db_path=Path(tmp) / "alerts.sqlite",
            )

        self.assertEqual(len(data.alerts), 1)
        self.assertEqual(data.alerts[0].region, "KEN")
        self.assertEqual(data.alerts[0].severity, "warning")
        self.assertIn("66", data.alerts[0].title)

    def test_loader_error_renders_safe_fallback_without_trace(self) -> None:
        fake = FakeStreamlit()

        def boom() -> object:
            raise RuntimeError("C:\\Users\\peorr\\Downloads\\secret.json")

        render_dashboard(data_loader=boom, streamlit_module=fake)  # type: ignore[arg-type]

        self.assertEqual(fake.page_config["layout"], "wide")
        self.assertTrue(fake.html_calls)
        html = fake.html_calls[0]
        self.assertIn(SAFE_ERROR_MESSAGE, html)
        self.assertIn("Dashboard data could not be loaded", html)
        self.assertNotIn("Traceback", html)
        self.assertNotIn("RuntimeError", html)
        self.assertNotIn("secret.json", html)
        self.assertNotIn("C:\\Users", html)

    def test_render_prefers_components_html_for_svg_support(self) -> None:
        fake = FakeStreamlitWithComponents()

        render_dashboard(data_loader=lambda: load_dashboard_shell_data("demo"), streamlit_module=fake)

        self.assertFalse(fake.html_calls)
        self.assertTrue(fake.components.v1.html_calls)
        html, height, scrolling = fake.components.v1.html_calls[0]
        self.assertEqual(height, 900)
        self.assertTrue(scrolling)
        self.assertIn("<svg", html)
        self.assertIn('fill="#c93636"', html)

    def test_layout_contract_prevents_horizontal_scroll(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("overflow-x: hidden", html)
        self.assertIn("minmax(0, 1fr)", html)
        self.assertIn("min-width: 0", html)
        self.assertIn("max-width: 1366px", html)


def _risk_snapshot(
    *,
    region_id: str = "ken",
    risk_level: str = "emergency",
    score: float = 82.0,
    is_simulated: bool = False,
) -> RiskSnapshot:
    return RiskSnapshot(
        region_id=region_id,
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-08T00:00:00Z",
        composite_score=score,
        risk_level=risk_level,
        contributing_indicators=("ndvi", "rainfall_mm"),
        source="mwangaza.risk.composite",
        quality_flag="ok",
        is_simulated=is_simulated,
        metadata={"model_version": "composite-risk-v1", "updated_at": "2026-07-09T00:00:00Z"},
    )


def _json_payload(risk: RiskSnapshot) -> dict[str, object]:
    return json.loads(json.dumps(risk.to_dict()))


if __name__ == "__main__":
    unittest.main()

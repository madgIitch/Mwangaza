from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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


class DashboardShellTests(unittest.TestCase):
    def test_home_shell_shows_brand_update_and_data_status(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data())

        self.assertIn("Mwangaza", html)
        self.assertIn("Bringing Light to Early Action", html)
        self.assertIn("Last update:", html)
        self.assertIn("Data is current", html)

    def test_navigation_contains_required_sections(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data())

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
        self.assertIn("0.31", {metric.value for metric in data.metrics})
        self.assertIn("Activate urgent coordination review", data.recommendations[0])

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

    def test_layout_contract_prevents_horizontal_scroll(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data())

        self.assertIn("overflow-x: hidden", html)
        self.assertIn("minmax(0, 1fr)", html)
        self.assertIn("min-width: 0", html)
        self.assertIn("max-width: 1366px", html)


def _risk_snapshot(
    *,
    risk_level: str = "emergency",
    score: float = 82.0,
    is_simulated: bool = False,
) -> RiskSnapshot:
    return RiskSnapshot(
        region_id="ken",
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


if __name__ == "__main__":
    unittest.main()

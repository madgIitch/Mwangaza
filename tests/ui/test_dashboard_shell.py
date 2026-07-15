from __future__ import annotations

import unittest

from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import SAFE_ERROR_MESSAGE, build_dashboard_shell_html, render_dashboard


class FakeStreamlit:
    def __init__(self) -> None:
        self.page_config: dict[str, object] | None = None
        self.markdown_calls: list[tuple[str, bool]] = []

    def set_page_config(self, **kwargs: object) -> None:
        self.page_config = kwargs

    def markdown(self, body: str, *, unsafe_allow_html: bool = False) -> None:
        self.markdown_calls.append((body, unsafe_allow_html))


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

    def test_loader_error_renders_safe_fallback_without_trace(self) -> None:
        fake = FakeStreamlit()

        def boom() -> object:
            raise RuntimeError("C:\\Users\\peorr\\Downloads\\secret.json")

        render_dashboard(data_loader=boom, streamlit_module=fake)  # type: ignore[arg-type]

        self.assertEqual(fake.page_config["layout"], "wide")
        self.assertTrue(fake.markdown_calls)
        html = fake.markdown_calls[0][0]
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


if __name__ == "__main__":
    unittest.main()

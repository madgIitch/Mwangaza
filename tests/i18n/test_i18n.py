from __future__ import annotations

import unittest
from unittest.mock import patch

from mwangaza.i18n import AVAILABLE_LANGUAGES, CATALOGS, translate, validate_catalogs
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import build_dashboard_shell_html


class I18nTests(unittest.TestCase):
    def test_available_languages_are_exactly_required(self) -> None:
        self.assertEqual(AVAILABLE_LANGUAGES, ("en", "sw", "so"))
        validate_catalogs()

    def test_translate_navigation_levels_and_recommendations(self) -> None:
        self.assertEqual(translate("nav.alerts", language="sw").value, "Tahadhari")
        self.assertEqual(translate("risk.critical", language="so").value, "Halis sare")
        self.assertEqual(translate("recommendation.prepare", language="sw").value, "Andaa orodha ya hatua za mapema.")

    def test_missing_key_falls_back_to_english_and_warns(self) -> None:
        result = translate("missing.key", language="so")

        self.assertEqual(result.value, "missing.key")
        self.assertEqual(result.warnings, ("missing translation: so.missing.key",))

    def test_validate_catalogs_fails_on_missing_required_key(self) -> None:
        broken = {lang: dict(catalog) for lang, catalog in CATALOGS.items()}
        del broken["sw"]["nav.alerts"]

        with self.assertRaisesRegex(ValueError, "missing i18n keys"):
            validate_catalogs(broken)

    def test_language_changes_ui_text_but_not_values_or_iso_dates(self) -> None:
        with patch.dict("os.environ", {"MWANGAZA_LANG": "sw"}):
            html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Tahadhari", html)
        self.assertIn("Ripoti", html)
        self.assertIn('data-language="sw"', html)
        self.assertIn("MODIS/061/MOD13Q1", html)
        self.assertIn("2026-07-15", html)
        self.assertIn("78", html)


if __name__ == "__main__":
    unittest.main()

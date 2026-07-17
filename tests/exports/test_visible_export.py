from __future__ import annotations

import csv
import io
import json
import unittest

from mwangaza.exports import (
    SCHEMA_VERSION,
    build_visible_export,
    export_visible_csv,
    export_visible_json,
    safe_export_filename,
)
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import build_dashboard_shell_html


class VisibleExportTests(unittest.TestCase):
    def test_csv_and_json_share_visible_values_units_and_quality(self) -> None:
        export = build_visible_export(load_dashboard_shell_data("demo"), max_rows=20)

        raw_json = json.loads(export_visible_json(export))
        raw_csv = list(csv.DictReader(io.StringIO(export_visible_csv(export))))

        json_rows = raw_json["rows"]
        self.assertEqual(raw_json["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(raw_csv), len(json_rows))
        for csv_row, json_row in zip(raw_csv, json_rows, strict=True):
            self.assertEqual(csv_row["name"], json_row["name"])
            self.assertEqual(csv_row["unit"], json_row["unit"])
            self.assertEqual(csv_row["quality"], json_row["quality"])
        self.assertIn("source_metadata", raw_json)
        self.assertIn("data_source", raw_json["source_metadata"])

    def test_export_sanitizes_secrets_paths_and_omits_geometry_by_default(self) -> None:
        data = load_dashboard_shell_data("demo")
        export = build_visible_export(data, max_rows=2)
        raw = export_visible_json(export)

        self.assertNotIn("private_key", raw.lower())
        self.assertNotIn("token", raw.lower())
        self.assertNotIn("C:\\", raw)
        self.assertNotIn("ui_geometry", raw)

        with_geometry = export_visible_json(build_visible_export(data, max_rows=1, include_geometry=True))
        self.assertIn("ui_geometry", with_geometry)

    def test_export_limits_rows_and_keeps_nulls_as_null_or_empty(self) -> None:
        export = build_visible_export(load_dashboard_shell_data("demo"), region_id="ken", max_rows=10)

        raw_json = json.loads(export_visible_json(export))
        raw_csv = list(csv.DictReader(io.StringIO(export_visible_csv(export))))

        self.assertLessEqual(len(raw_json["rows"]), 10)
        null_rows = [row for row in raw_json["rows"] if row["value"] is None]
        self.assertTrue(null_rows)
        csv_null_rows = [row for row in raw_csv if row["name"] == null_rows[0]["name"]]
        self.assertEqual(csv_null_rows[0]["value"], "")

    def test_export_filename_is_safe_and_dashboard_announces_export_contract(self) -> None:
        export = build_visible_export(load_dashboard_shell_data("demo"))
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertEqual(
            safe_export_filename(export, "json"),
            "mwangaza-visible-export-somalia-2026-07-01-to-2026-07-15.json",
        )
        self.assertIn('data-export-summary="visible-snapshot"', html)
        self.assertIn("row limit 500", html)
        self.assertIn("geometry omitted by default", html)
        self.assertIn('data-export-filename="csv"', html)
        self.assertIn('data-export-filename="json"', html)

    def test_rejects_invalid_row_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_rows"):
            build_visible_export(load_dashboard_shell_data("demo"), max_rows=0)


if __name__ == "__main__":
    unittest.main()

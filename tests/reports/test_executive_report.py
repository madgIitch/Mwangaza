from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from mwangaza.reports import (
    build_executive_report_context,
    render_executive_report_html,
    render_executive_report_pdf,
    safe_report_filename,
)
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import build_dashboard_shell_html


class ExecutiveReportTests(unittest.TestCase):
    def test_context_uses_selected_snapshot_metrics_quality_and_recommendations(self) -> None:
        data = load_dashboard_shell_data("demo")

        context = build_executive_report_context(
            data,
            generated_at=datetime(2026, 7, 17, 10, 30, tzinfo=UTC),
        )

        self.assertEqual(context.region_id, "som")
        self.assertEqual(context.region_label, "Somalia")
        self.assertEqual(context.period_label, "2026-07-01 to 2026-07-15")
        self.assertEqual(context.score, "78/100")
        self.assertEqual(context.quality, "Good")
        self.assertIn("Prioritize water trucking readiness in high-risk districts.", context.recommendations)
        self.assertIn("potentially_exposed", {metric.label for metric in context.metrics})

    def test_html_includes_sources_versions_limitations_and_snapshot_bars(self) -> None:
        context = build_executive_report_context(
            load_dashboard_shell_data("demo"),
            generated_at=datetime(2026, 7, 17, 10, 30, tzinfo=UTC),
        )

        html = render_executive_report_html(context)

        self.assertIn("Mwangaza Executive Report", html)
        self.assertIn("Region: Somalia", html)
        self.assertIn("Period: 2026-07-01 to 2026-07-15", html)
        self.assertIn("Snapshot Indicators", html)
        self.assertIn('data-metric="Composite score"', html)
        self.assertIn("potentially_exposed", html)
        self.assertIn("demo/synthetic", html)
        self.assertIn("not measured impact", html)
        self.assertNotIn("Dashboard Link", html)

    def test_qr_uses_configured_url_and_is_omitted_without_url(self) -> None:
        without_url = build_executive_report_context(load_dashboard_shell_data("demo"))
        with_url = build_executive_report_context(
            load_dashboard_shell_data("demo"),
            dashboard_url="https://example.org/mwangaza?region=som",
        )

        self.assertEqual(without_url.dashboard_url, "")
        self.assertEqual(without_url.qr_matrix, ())
        self.assertIn("Dashboard Link", render_executive_report_html(with_url))
        self.assertIn("https://example.org/mwangaza?region=som", render_executive_report_html(with_url))
        self.assertEqual(len(with_url.qr_matrix), 9)

    def test_pdf_bytes_and_filename_are_safe_and_deterministic(self) -> None:
        context = build_executive_report_context(load_dashboard_shell_data("demo"))

        pdf = render_executive_report_pdf(context)
        filename = safe_report_filename(context)

        self.assertTrue(pdf.startswith(b"%PDF-HTML\n"))
        self.assertIn(b"Mwangaza Executive Report", pdf)
        self.assertEqual(filename, "mwangaza-executive-report-somalia-2026-07-01-to-2026-07-15.pdf")
        self.assertNotIn("\\", filename)
        self.assertNotIn("/", filename)

    def test_report_generation_does_not_query_live_gee(self) -> None:
        data = load_dashboard_shell_data("demo")
        with patch("mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads") as live:
            context = build_executive_report_context(data)
            render_executive_report_html(context)
            render_executive_report_pdf(context)

        live.assert_not_called()

    def test_dashboard_reports_panel_exposes_filename_and_optional_qr_status(self) -> None:
        with patch.dict("os.environ", {"MWANGAZA_DASHBOARD_URL": "https://example.org/mwangaza"}):
            html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Executive Report", html)
        self.assertIn("data-report-filename", html)
        self.assertIn("mwangaza-executive-report-somalia-2026-07-01-to-2026-07-15.pdf", html)
        self.assertIn('data-report-qr="configured"', html)


if __name__ == "__main__":
    unittest.main()

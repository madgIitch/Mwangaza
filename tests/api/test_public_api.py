from __future__ import annotations

import asyncio
import importlib
import json
import os
import unittest
from unittest.mock import patch

from mwangaza.api.app import app

api_app = importlib.import_module("mwangaza.api.app")


class PublicApiTests(unittest.TestCase):
    def setUp(self) -> None:
        api_app._DASHBOARD_CACHE = None
        api_app._DASHBOARD_REFRESHING = False

    def tearDown(self) -> None:
        api_app._DASHBOARD_CACHE = None
        api_app._DASHBOARD_REFRESHING = False

    def test_v1_regions_is_paginated_and_versioned(self) -> None:
        status, headers, payload = _request("/api/v1/regions", b"limit=2&offset=1")

        self.assertEqual(status, 200)
        self.assertEqual(payload["schema_version"], "mwangaza.api.v1")
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(len(payload["items"]), 2)
        self.assertIn("cache-control", headers)

    def test_latest_snapshot_uses_visible_export_contract(self) -> None:
        with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
            status, _headers, payload = _request("/api/v1/snapshots/latest")

        self.assertEqual(status, 200)
        self.assertEqual(payload["schema_version"], "mwangaza.api.v1")
        self.assertEqual(payload["snapshot"]["region_id"], "som")
        self.assertIn("source_metadata", payload["snapshot"])
        self.assertIn("regional_risk", payload["snapshot"])
        self.assertTrue(payload["snapshot"]["regional_risk"])
        self.assertIn("ui_geometry", payload["snapshot"]["regional_risk"][0])
        self.assertTrue(payload["snapshot"]["region_profiles"])
        profile = payload["snapshot"]["region_profiles"][0]
        self.assertTrue(profile["pilot_units"])
        self.assertIn("administrative_units", profile)
        self.assertTrue(profile["trends"])
        self.assertIn("baseline_label", profile["trends"][0])
        self.assertTrue(profile["historical_rows"])
        self.assertTrue(profile["contributions"])
        self.assertTrue(all("weighted_contribution" in item for item in profile["contributions"]))
        matching_region = next(
            item for item in payload["snapshot"]["regional_risk"] if item["id"] == profile["id"]
        )
        self.assertAlmostEqual(
            sum(item["weighted_contribution"] for item in profile["contributions"]),
            matching_region["score"],
            places=2,
        )
        self.assertTrue(payload["snapshot"]["rows"])

    def test_alerts_and_forecasts_endpoints_exist(self) -> None:
        with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
            alerts_status, _headers, alerts = _request("/api/v1/alerts", b"limit=1")
            forecasts_status, _headers, forecasts = _request("/api/v1/forecasts")

        self.assertEqual(alerts_status, 200)
        self.assertEqual(alerts["limit"], 1)
        self.assertEqual(len(alerts["items"]), 1)
        self.assertEqual(forecasts_status, 200)
        self.assertFalse(forecasts["available"])
        self.assertEqual(forecasts["items"], [])

    def test_alerts_publish_stable_ids_and_detail_route(self) -> None:
        with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
            status, _headers, alerts = _request("/api/v1/alerts")
            alert_id = alerts["items"][0]["id"]
            detail_status, _headers, detail = _request(f"/api/v1/alerts/{alert_id}")
            missing_status, _headers, missing = _request("/api/v1/alerts/ALT-MISSING")

        self.assertEqual(status, 200)
        self.assertTrue(alert_id.startswith("ALT-"))
        self.assertEqual(detail_status, 200)
        self.assertEqual(detail["alert"]["id"], alert_id)
        self.assertTrue(detail["alert"]["evidence"])
        self.assertEqual(missing_status, 404)
        self.assertEqual(missing["error"]["code"], "not_found")

    def test_report_and_snapshot_downloads_are_real_and_context_bound(self) -> None:
        period = "2026-07-01 to 2026-07-15"
        encoded = b"region=som&period=2026-07-01+to+2026-07-15"
        with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
            pdf_status, pdf_headers, pdf = _raw_request("/api/v1/reports/executive", encoded)
            csv_status, csv_headers, csv_body = _raw_request("/api/v1/exports/snapshot", encoded + b"&format=csv")
            json_status, json_headers, json_body = _raw_request("/api/v1/exports/snapshot", encoded + b"&format=json")
            invalid_status, _headers, invalid = _request("/api/v1/exports/snapshot", b"region=som&period=wrong&format=csv")

        self.assertEqual(pdf_status, 200)
        self.assertEqual(pdf_headers["content-type"], "application/pdf")
        self.assertIn("attachment; filename=", pdf_headers["content-disposition"])
        self.assertTrue(pdf.startswith(b"%PDF-HTML"))
        self.assertEqual(csv_status, 200)
        self.assertTrue(csv_headers["content-type"].startswith("text/csv"))
        self.assertIn(b"row_type,region_id", csv_body)
        self.assertNotIn(b"ui_geometry", csv_body)
        self.assertEqual(json_status, 200)
        self.assertEqual(json_headers["content-type"], "application/json")
        self.assertEqual(json.loads(json_body)["period"], period)
        self.assertEqual(invalid_status, 400)
        self.assertEqual(invalid["error"]["code"], "invalid_request")

    def test_v1_endpoints_do_not_call_live_gee_loader(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}),
            patch("mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads") as live,
        ):
            _request("/api/v1/snapshots/latest")
            _request("/api/v1/alerts")

        live.assert_not_called()

    def test_explicit_demo_mode_adds_metadata_without_gee(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_MODE": "demo"}, clear=True),
            patch("mwangaza.api.app.check_gee_auth") as gee,
        ):
            status, _headers, payload = _request("/api/v1/snapshots/latest")
            health_status, _headers, health = _request("/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["is_demo"])
        self.assertEqual(payload["data_mode"], "demo")
        self.assertIn("reference_date", payload)
        self.assertEqual(health_status, 200)
        self.assertEqual(health["gee"]["status"], "not_initialized")
        gee.assert_not_called()

    def test_production_rejects_implicit_demo_fallback(self) -> None:
        from mwangaza.services.dashboard_shell import load_dashboard_shell_data
        demo = load_dashboard_shell_data("demo")
        with (
            patch.dict(os.environ, {"MWANGAZA_MODE": "production"}, clear=True),
            patch("mwangaza.api.app.load_materialized_dashboard_shell_data", return_value=None),
            patch("mwangaza.api.app.load_dashboard_shell_data", return_value=demo),
        ):
            status, _headers, payload = _request("/api/v1/snapshots/latest")
        self.assertEqual(status, 500)
        self.assertEqual(payload["error"]["code"], "internal_error")
        self.assertNotIn("is_demo", payload)

    def test_live_api_mode_uses_dashboard_loader_without_forcing_demo(self) -> None:
        from mwangaza.services.dashboard_shell import load_dashboard_shell_data

        demo = load_dashboard_shell_data("demo")
        with (
            patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "live"}),
            patch("mwangaza.api.app.load_materialized_dashboard_shell_data", return_value=None),
            patch("mwangaza.api.app.load_dashboard_shell_data", return_value=demo) as loader,
        ):
            status, _headers, payload = _request("/api/v1/snapshots/latest")

        self.assertEqual(status, 200)
        self.assertIn(payload["data_mode"], {"live", "cache", "demo"})
        loader.assert_called_with()

    def test_live_api_mode_reuses_dashboard_loader_cache_across_endpoints(self) -> None:
        from mwangaza.services.dashboard_shell import load_dashboard_shell_data

        demo = load_dashboard_shell_data("demo")
        with (
            patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "live"}),
            patch("mwangaza.api.app.load_materialized_dashboard_shell_data", return_value=None),
            patch("mwangaza.api.app.load_dashboard_shell_data", return_value=demo) as loader,
        ):
            _request("/api/v1/snapshots/latest")
            _request("/api/v1/alerts")

        self.assertEqual(loader.call_count, 1)

    def test_live_api_serves_materialized_data_and_refreshes_without_blocking(self) -> None:
        from mwangaza.services.dashboard_shell import load_dashboard_shell_data

        cached = load_dashboard_shell_data("cache")
        with (
            patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "live"}),
            patch("mwangaza.api.app.load_materialized_dashboard_shell_data", return_value=cached),
            patch("mwangaza.api.app._start_dashboard_refresh") as refresh,
            patch("mwangaza.api.app.load_dashboard_shell_data") as live_loader,
        ):
            status, _headers, payload = _request("/api/v1/snapshots/latest")
            alerts_status, _headers, _alerts = _request("/api/v1/alerts")
            forecasts_status, _headers, _forecasts = _request("/api/v1/forecasts")

        self.assertEqual(status, 200)
        self.assertEqual(payload["data_mode"], "cache")
        self.assertEqual(alerts_status, 200)
        self.assertEqual(forecasts_status, 200)
        refresh.assert_called_once_with()
        live_loader.assert_not_called()

    def test_explicit_cache_mode_never_starts_live_refresh(self) -> None:
        from mwangaza.services.dashboard_shell import load_dashboard_shell_data

        cached = load_dashboard_shell_data("cache")
        with (
            patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "cache"}),
            patch("mwangaza.api.app.load_materialized_dashboard_shell_data", return_value=cached),
            patch("mwangaza.api.app._start_dashboard_refresh") as refresh,
            patch("mwangaza.api.app.load_dashboard_shell_data") as live_loader,
        ):
            status, _headers, payload = _request("/api/v1/snapshots/latest")

        self.assertEqual(status, 200)
        self.assertEqual(payload["data_mode"], "cache")
        refresh.assert_not_called()
        live_loader.assert_not_called()

    def test_errors_are_structured_and_sanitized(self) -> None:
        status, _headers, payload = _request("/api/v1/regions", b"limit=not-an-int")

        self.assertEqual(status, 400)
        self.assertEqual(set(payload), {"error"})
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertNotIn("Traceback", json.dumps(payload))
        self.assertNotIn("C:\\", json.dumps(payload))

    def test_openapi_contains_v1_examples_and_health_still_exists(self) -> None:
        openapi_status, _headers, openapi = _request("/openapi.json")
        health_status, _headers, health = _request("/health")

        self.assertEqual(openapi_status, 200)
        self.assertIn("/api/v1/regions", openapi["paths"])
        self.assertIn("/api/v1/alerts/{alert_id}", openapi["paths"])
        self.assertIn("/api/v1/reports/executive", openapi["paths"])
        self.assertIn("/api/v1/exports/snapshot", openapi["paths"])
        self.assertIn("x-example", openapi["paths"]["/api/v1/regions"]["get"])
        self.assertEqual(health_status, 200)
        self.assertIn("gee", health)


def _request(path: str, query_string: bytes = b"") -> tuple[int, dict[str, str], dict[str, object]]:
    status, headers, body = _raw_request(path, query_string)
    return status, headers, json.loads(body)


def _raw_request(path: str, query_string: bytes = b"") -> tuple[int, dict[str, str], bytes]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(app({"type": "http", "path": path, "query_string": query_string}, receive, send))
    start = messages[0]
    body = messages[1]
    headers = {
        key.decode("ascii"): value.decode("ascii")
        for key, value in start.get("headers", [])  # type: ignore[union-attr]
    }
    return int(start["status"]), headers, body["body"]  # type: ignore[return-value]


if __name__ == "__main__":
    unittest.main()

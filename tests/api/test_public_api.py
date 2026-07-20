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

    def tearDown(self) -> None:
        api_app._DASHBOARD_CACHE = None

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
            patch("mwangaza.api.app.load_dashboard_shell_data", return_value=demo) as loader,
        ):
            _request("/api/v1/snapshots/latest")
            _request("/api/v1/alerts")

        self.assertEqual(loader.call_count, 1)

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
        self.assertIn("x-example", openapi["paths"]["/api/v1/regions"]["get"])
        self.assertEqual(health_status, 200)
        self.assertIn("gee", health)


def _request(path: str, query_string: bytes = b"") -> tuple[int, dict[str, str], dict[str, object]]:
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
    return int(start["status"]), headers, json.loads(body["body"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

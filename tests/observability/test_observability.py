from __future__ import annotations

import json
import tempfile
import unittest
import asyncio
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mwangaza.observability import METRICS, emit, readiness_status, redact, resolve_run_id, structured_event
from mwangaza.api.app import app


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        METRICS.reset()

    def test_structured_event_has_required_fields_and_json_output(self) -> None:
        event = structured_event("request complete", run_id="run-12345678", duration_ms=12)
        self.assertEqual(event["run_id"], "run-12345678")
        self.assertEqual(event["component"], "api")
        self.assertIn("timestamp", event)
        output = StringIO()
        with redirect_stdout(output):
            emit("request complete", run_id="run-12345678")
        self.assertEqual(json.loads(output.getvalue())["event"], "request complete")

    def test_redaction_is_recursive_and_removes_paths_and_known_secrets(self) -> None:
        value = {"nested": [{"token": "secret-value"}], "message": "failed secret-value", "path": Path("C:/private/data")}
        redacted = redact(value, env={"MWANGAZA_GEE_PRIVATE_KEY_JSON": "secret-value"})
        self.assertEqual(redacted["nested"][0]["token"], "[REDACTED]")
        self.assertNotIn("secret-value", json.dumps(redacted))
        self.assertEqual(redacted["path"], "[LOCAL_PATH]")

    def test_run_id_preserves_valid_input_and_replaces_invalid_input(self) -> None:
        self.assertEqual(resolve_run_id("judge-run-123"), "judge-run-123")
        self.assertNotEqual(resolve_run_id("bad id"), "bad id")

    def test_readiness_reports_database_and_required_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ready = readiness_status({"MWANGAZA_ADMIN_DB": str(Path(tmp) / "admin.sqlite")})
            unavailable = readiness_status({
                "MWANGAZA_ADMIN_DB": str(Path(tmp) / "admin.sqlite"),
                "MWANGAZA_CACHE_REQUIRED": "true",
                "MWANGAZA_CACHE_DIR": str(Path(tmp) / "missing"),
            })
        self.assertTrue(ready.ready)
        self.assertFalse(unavailable.ready)
        self.assertEqual(unavailable.checks["cache"], "unavailable")

    def test_metrics_are_aggregated(self) -> None:
        METRICS.record_request(20)
        METRICS.record_request(40, error=True)
        METRICS.record_cache(True)
        METRICS.observe_workload(regions_processed=3, active_alerts=2)
        snapshot = METRICS.snapshot()
        self.assertEqual(snapshot["duration_ms_average"], 30)
        self.assertEqual(snapshot["errors_total"], 1)
        self.assertEqual(snapshot["active_alerts"], 2)

    def test_api_propagates_run_id_and_exposes_readiness_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"MWANGAZA_ADMIN_DB": str(Path(tmp) / "admin.sqlite")}
            with patch.dict("os.environ", env, clear=False):
                status, headers, payload = _request("/api/v1/observability", [(b"x-run-id", b"judge-run-123")])
                ready_status, ready_headers, ready_payload = _request("/ready", [(b"x-run-id", b"judge-run-456")])
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-run-id"], "judge-run-123")
        self.assertEqual(payload["run_id"], "judge-run-123")
        self.assertEqual(ready_status, 200)
        self.assertEqual(ready_headers["x-run-id"], "judge-run-456")
        self.assertTrue(ready_payload["ready"])

    def test_earth_engine_error_is_correlated_without_sensitive_details(self) -> None:
        output = StringIO()
        with patch("mwangaza.api.app.check_gee_auth") as gee_check, redirect_stdout(output):
            gee_check.return_value.to_public_dict.return_value = {
                "status": "auth_error",
                "configured": True,
                "message": "Earth Engine authentication failed",
            }
            status, headers, payload = _request("/health", [(b"x-run-id", b"gee-failure-123")])
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        health_event = next(event for event in events if event["event"] == "health checked")
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-run-id"], "gee-failure-123")
        self.assertEqual(payload["observability"]["run_id"], "gee-failure-123")
        self.assertEqual(health_event["run_id"], "gee-failure-123")
        self.assertNotIn("private_key", output.getvalue())


def _request(path: str, headers: list[tuple[bytes, bytes]]) -> tuple[int, dict[str, str], dict[str, object]]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(app({"type": "http", "path": path, "query_string": b"", "headers": headers}, receive, send))
    start, response = messages
    response_headers = {key.decode("ascii"): value.decode("ascii") for key, value in start["headers"]}  # type: ignore[index]
    return int(start["status"]), response_headers, json.loads(response["body"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

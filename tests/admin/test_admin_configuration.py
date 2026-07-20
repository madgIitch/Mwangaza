from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from mwangaza.admin import (
    AdminConfigurationRepository,
    default_admin_configuration,
    validate_admin_configuration,
)
from mwangaza.api.app import app


class AdminConfigurationTests(unittest.TestCase):
    def test_repository_versions_are_append_only_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AdminConfigurationRepository(os.path.join(tmp, "admin.sqlite"))
            initial_versions = repo.list_versions()
            config = default_admin_configuration()
            config["thresholds"] = {**config["thresholds"], "label": "edited-prototype"}

            version = repo.create_version(config, actor="demo-admin")
            active = repo.get_active()
            events = repo.audit.list_events(event_type="configuration_saved")

            self.assertEqual(len(repo.list_versions()), len(initial_versions) + 1)
            self.assertEqual(version.status, "draft")
            self.assertIsNotNone(active)
            self.assertNotEqual(active.version_id, version.version_id)
            self.assertEqual(events[-1].entity_id, version.version_id)
            self.assertIn("content_hash_prefix", events[-1].metadata)
            repo.close()

    def test_invalid_configuration_is_not_activated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = AdminConfigurationRepository(os.path.join(tmp, "admin.sqlite"))
            active_before = repo.get_active()
            invalid = default_admin_configuration()
            invalid["thresholds"]["bands"] = []

            version = repo.create_version(invalid, actor="demo-admin")

            self.assertEqual(version.status, "rejected")
            self.assertTrue(version.validation_errors)
            self.assertEqual(repo.get_active().version_id, active_before.version_id)
            repo.close()

    def test_validation_reports_actionable_errors(self) -> None:
        invalid = {"schema_version": "wrong", "thresholds": {}, "actions": {}}

        errors = validate_admin_configuration(invalid)

        self.assertIn("schema_version must be mwangaza.admin.v1", errors)
        self.assertTrue(any("thresholds" in error for error in errors))
        self.assertTrue(any("actions" in error for error in errors))

    def test_api_exposes_complete_admin_config_without_credentials_and_does_not_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "MWANGAZA_ADMIN_DB": os.path.join(tmp, "admin.sqlite"),
            }
            with (
                patch.dict(os.environ, env, clear=False),
                patch("mwangaza.api.app.load_dashboard_shell_data") as loader,
            ):
                status, _headers, payload = _request(
                    "/api/v1/admin/config",
                )

            self.assertEqual(status, 200)
            self.assertFalse(payload["recalculation"]["triggered"])
            self.assertEqual(payload["security"]["access"], "public")
            self.assertEqual(payload["security"]["auth"], "none")
            loader.assert_not_called()

    def test_api_saves_new_version_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = default_admin_configuration()
            config["actions"]["templates"]["warning"]["action"] = "Brief partners from admin panel"
            env = {
                "MWANGAZA_ADMIN_DB": os.path.join(tmp, "admin.sqlite"),
            }
            with patch.dict(os.environ, env, clear=False):
                status, _headers, payload = _request(
                    "/api/v1/admin/config",
                    headers=[(b"content-type", b"application/json")],
                    body=json.dumps({"configuration": config}).encode("utf-8"),
                )

            serialized = json.dumps(payload)
            self.assertEqual(status, 201)
            self.assertEqual(payload["saved_version"]["status"], "draft")
            self.assertIn("Brief partners from admin panel", serialized)
            self.assertEqual(payload["security"]["auth"], "none")


def _request(
    path: str,
    *,
    query_string: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
    body: bytes = b"",
) -> tuple[int, dict[str, str], dict[str, object]]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(
        app(
            {"type": "http", "path": path, "query_string": query_string, "headers": headers or []},
            receive,
            send,
        )
    )
    start = messages[0]
    response_body = messages[1]
    response_headers = {
        key.decode("ascii"): value.decode("ascii")
        for key, value in start.get("headers", [])  # type: ignore[union-attr]
    }
    return int(start["status"]), response_headers, json.loads(response_body["body"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

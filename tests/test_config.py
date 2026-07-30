from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mwangaza.api.app import app
from mwangaza.config import ConfigurationError, load_settings

SECRET_ACCOUNT = "svc-secret@example.test"
SECRET_JSON = '{"private_key":"do-not-print","client_email":"svc-secret@example.test"}'


class SettingsTests(unittest.TestCase):
    def test_local_defaults_do_not_need_secrets(self) -> None:
        settings = load_settings({})
        self.assertEqual(settings.environment, "local")
        self.assertEqual(settings.enabled_countries, ("KEN", "ETH", "SOM", "SDN", "SSD", "UGA", "DJI", "ERI"))
        self.assertIsNone(settings.gee_service_account)
        self.assertNotIn(SECRET_ACCOUNT, repr(settings))
        self.assertNotIn("do-not-print", repr(settings))

    def test_test_profile_does_not_use_real_environment(self) -> None:
        with patch.dict(os.environ, {"MWANGAZA_GEE_SERVICE_ACCOUNT": SECRET_ACCOUNT}, clear=True):
            settings = load_settings({"MWANGAZA_ENV": "test"})
        self.assertEqual(settings.environment, "test")
        self.assertIsNone(settings.gee_service_account)

    def test_demo_profile_uses_fixture_dir_without_gee(self) -> None:
        settings = load_settings(
            {
                "MWANGAZA_ENV": "demo",
                "MWANGAZA_DEMO_FIXTURE_DIR": "./fixtures/demo",
            }
        )
        self.assertEqual(settings.environment, "demo")
        self.assertEqual(str(settings.demo_fixture_dir), "fixtures\\demo" if os.name == "nt" else "fixtures/demo")
        self.assertIsNone(settings.gee_private_key_json)

    def test_production_missing_secrets_lists_variable_names_only(self) -> None:
        with self.assertRaises(ConfigurationError) as ctx:
            load_settings({"MWANGAZA_ENV": "production"})
        message = str(ctx.exception)
        self.assertIn("MWANGAZA_GEE_PROJECT", message)
        self.assertIn("MWANGAZA_GEE_SERVICE_ACCOUNT", message)
        self.assertIn("MWANGAZA_GEE_PRIVATE_KEY_JSON", message)
        self.assertNotIn(SECRET_ACCOUNT, message)
        self.assertNotIn("private_key", message)

    def test_production_cache_reader_does_not_require_gee_credentials(self) -> None:
        settings = load_settings(
            {"MWANGAZA_ENV": "production", "MWANGAZA_API_DATA_MODE": "cache"}
        )

        self.assertEqual(settings.environment, "production")
        self.assertIsNone(settings.gee_project)
        self.assertIsNone(settings.gee_private_key_json)

    def test_production_rejects_placeholders(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_settings(
                {
                    "MWANGAZA_ENV": "production",
                    "MWANGAZA_GEE_PROJECT": "replace-me",
                    "MWANGAZA_GEE_SERVICE_ACCOUNT": "replace-me",
                    "MWANGAZA_GEE_PRIVATE_KEY_JSON": "replace-me",
                }
            )

    def test_invalid_dates_and_country_fail(self) -> None:
        with self.assertRaises(ConfigurationError) as ctx:
            load_settings(
                {
                    "MWANGAZA_CLIMATOLOGY_START_YEAR": "2021",
                    "MWANGAZA_CLIMATOLOGY_END_YEAR": "2020",
                    "MWANGAZA_ENABLED_COUNTRIES": "KEN,XXX",
                }
            )
        self.assertIn("MWANGAZA_ENABLED_COUNTRIES", str(ctx.exception))
        self.assertIn("MWANGAZA_CLIMATOLOGY_START_YEAR", str(ctx.exception))

    def test_secret_json_must_be_object_when_present(self) -> None:
        with self.assertRaises(ConfigurationError):
            load_settings({"MWANGAZA_GEE_PRIVATE_KEY_JSON": "not-json"})

    def test_repr_and_public_dict_redact_private_values(self) -> None:
        settings = load_settings(
            {
                "MWANGAZA_ENV": "production",
                "MWANGAZA_GEE_PROJECT": "demo-project",
                "MWANGAZA_GEE_SERVICE_ACCOUNT": SECRET_ACCOUNT,
                "MWANGAZA_GEE_PRIVATE_KEY_JSON": SECRET_JSON,
            }
        )
        self.assertNotIn(SECRET_ACCOUNT, repr(settings))
        self.assertNotIn("do-not-print", repr(settings))
        public = json.dumps(settings.to_public_dict())
        self.assertNotIn(SECRET_ACCOUNT, public)
        self.assertNotIn("do-not-print", public)

    def test_load_settings_reads_dotenv_from_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text(
                "\n".join(
                    [
                        "MWANGAZA_ENV=production",
                        "MWANGAZA_GEE_PROJECT=dotenv-project",
                        f"MWANGAZA_GEE_SERVICE_ACCOUNT={SECRET_ACCOUNT}",
                        f"MWANGAZA_GEE_PRIVATE_KEY_JSON={SECRET_JSON}",
                    ]
                ),
                encoding="utf-8",
            )
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                with patch.dict(os.environ, {}, clear=True):
                    settings = load_settings()
            finally:
                os.chdir(old_cwd)

        self.assertEqual(settings.environment, "production")
        self.assertEqual(settings.gee_project, "dotenv-project")
        self.assertEqual(settings.gee_service_account, SECRET_ACCOUNT)
        self.assertEqual(settings.gee_private_key_json, SECRET_JSON)

    def test_explicit_environment_mapping_does_not_read_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text("MWANGAZA_ENV=production\n", encoding="utf-8")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                settings = load_settings({})
            finally:
                os.chdir(old_cwd)

        self.assertEqual(settings.environment, "local")

    def test_real_environment_overrides_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".env").write_text(
                "\n".join(
                    [
                        "MWANGAZA_ENV=production",
                        "MWANGAZA_GEE_PROJECT=dotenv-project",
                        f"MWANGAZA_GEE_SERVICE_ACCOUNT={SECRET_ACCOUNT}",
                        f"MWANGAZA_GEE_PRIVATE_KEY_JSON={SECRET_JSON}",
                    ]
                ),
                encoding="utf-8",
            )
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                with patch.dict(os.environ, {"MWANGAZA_ENV": "test"}, clear=True):
                    settings = load_settings()
            finally:
                os.chdir(old_cwd)

        self.assertEqual(settings.environment, "test")


class HealthConfigTests(unittest.TestCase):
    def test_health_response_is_sanitized(self) -> None:
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        with patch.dict(
            os.environ,
            {
                "MWANGAZA_ENV": "production",
                "MWANGAZA_GEE_PROJECT": "demo-project",
                "MWANGAZA_GEE_SERVICE_ACCOUNT": SECRET_ACCOUNT,
                "MWANGAZA_GEE_PRIVATE_KEY_JSON": SECRET_JSON,
            },
            clear=True,
        ):
            asyncio.run(app({"type": "http", "path": "/health"}, receive, send))

        body = json.loads(messages[1]["body"])
        serialized = json.dumps(body)
        self.assertTrue(body["config_valid"])
        self.assertEqual(body["environment"], "production")
        self.assertNotIn(SECRET_ACCOUNT, serialized)
        self.assertNotIn("do-not-print", serialized)


if __name__ == "__main__":
    unittest.main()

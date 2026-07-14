from __future__ import annotations

import asyncio
import json
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from mwangaza.api.app import app
from mwangaza.config import load_settings
from mwangaza.gee.auth import STATUSES, check_gee_auth

SECRET_ACCOUNT = "svc-secret@example.test"
SECRET_JSON = '{"private_key":"do-not-print","client_email":"svc-secret@example.test"}'


@dataclass
class FakeData:
    error: Exception | None = None
    calls: int = 0

    def getAssetRoots(self) -> list[object]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return []


class FakeEe:
    def __init__(self, error: Exception | None = None) -> None:
        self.data = FakeData(error)
        self.credentials_args: tuple[object, ...] | None = None
        self.credentials_kwargs: dict[str, object] | None = None
        self.initialized_project: str | None = None

    def ServiceAccountCredentials(self, *args: object, **kwargs: object) -> object:
        self.credentials_args = args
        self.credentials_kwargs = kwargs
        return object()

    def Initialize(self, credentials: object, *, project: str | None = None) -> None:
        self.initialized_project = project


def production_settings() -> object:
    return load_settings(
        {
            "MWANGAZA_ENV": "production",
            "MWANGAZA_GEE_PROJECT": "demo-project",
            "MWANGAZA_GEE_SERVICE_ACCOUNT": SECRET_ACCOUNT,
            "MWANGAZA_GEE_PRIVATE_KEY_JSON": SECRET_JSON,
        }
    )


class GeeAuthTests(unittest.TestCase):
    def test_status_codes_are_stable(self) -> None:
        self.assertEqual(
            STATUSES,
            ("ok", "auth_error", "permission_error", "quota_error", "network_error"),
        )

    def test_missing_credentials_return_auth_error_without_importing_ee(self) -> None:
        result = check_gee_auth(load_settings({}))
        self.assertEqual(result.status, "auth_error")
        self.assertFalse(result.configured)
        self.assertEqual(result.attempts, 0)
        self.assertIn("MWANGAZA_GEE_PROJECT", result.missing_required_variables)

    def test_secret_json_passed_in_memory_to_fake_ee(self) -> None:
        fake = FakeEe()
        result = check_gee_auth(production_settings(), ee_module=fake)
        self.assertEqual(result.status, "ok")
        self.assertEqual(fake.initialized_project, "demo-project")
        self.assertEqual(fake.credentials_args, (SECRET_ACCOUNT,))
        self.assertEqual(fake.credentials_kwargs, {"key_data": json.loads(SECRET_JSON)})

    def test_invalid_json_shape_returns_auth_error(self) -> None:
        settings = load_settings(
            {
                "MWANGAZA_ENV": "test",
                "MWANGAZA_GEE_PROJECT": "demo-project",
                "MWANGAZA_GEE_SERVICE_ACCOUNT": SECRET_ACCOUNT,
                "MWANGAZA_GEE_PRIVATE_KEY_JSON": '{"client_email":"x"}',
            }
        )
        result = check_gee_auth(settings, ee_module=FakeEe())
        self.assertEqual(result.status, "auth_error")
        self.assertEqual(result.error_code, "invalid_service_account_json")

    def test_sdk_absent_returns_auth_error(self) -> None:
        with patch("importlib.import_module", side_effect=ModuleNotFoundError("ee")):
            result = check_gee_auth(production_settings())
        self.assertEqual(result.status, "auth_error")
        self.assertEqual(result.error_code, "sdk_unavailable")

    def test_error_mapping(self) -> None:
        cases = [
            (Exception("401 unauthorized credential revoked"), "auth_error"),
            (Exception("403 forbidden permission denied"), "permission_error"),
            (Exception("429 quota resource exhausted"), "quota_error"),
            (TimeoutError("timeout connecting to Earth Engine"), "network_error"),
            (Exception("surprising failure"), "network_error"),
        ]
        for exc, expected in cases:
            with self.subTest(expected=expected):
                result = check_gee_auth(
                    production_settings(),
                    ee_module=FakeEe(exc),
                    max_attempts=1,
                )
                self.assertEqual(result.status, expected)

    def test_retries_use_backoff_without_sleeping(self) -> None:
        delays: list[float] = []
        result = check_gee_auth(
            production_settings(),
            ee_module=FakeEe(TimeoutError("timeout")),
            max_attempts=3,
            base_delay_seconds=0.5,
            sleep=delays.append,
        )
        self.assertEqual(result.status, "network_error")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(delays, [0.5, 1.0])

    def test_health_response_contains_sanitized_gee(self) -> None:
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        with patch("mwangaza.api.app.check_gee_auth") as fake_check:
            fake_check.return_value = check_gee_auth(production_settings(), ee_module=FakeEe())
            asyncio.run(app({"type": "http", "path": "/health"}, receive, send))

        self.assertEqual(messages[0]["status"], 200)
        body = json.loads(messages[1]["body"])
        serialized = json.dumps(body)
        self.assertEqual(body["gee"]["status"], "ok")
        self.assertNotIn("demo-project", serialized)
        self.assertNotIn(SECRET_ACCOUNT, serialized)
        self.assertNotIn("do-not-print", serialized)


if __name__ == "__main__":
    unittest.main()

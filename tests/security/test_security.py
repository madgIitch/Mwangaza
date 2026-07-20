from __future__ import annotations

import tempfile
import unittest
import asyncio
import json
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from mwangaza.api.app import app
from mwangaza.security import MAX_BODY_BYTES, RATE_LIMITER, RateLimiter, SecurityRequestError, scan_files, validate_body_contract, validate_request_target


class SecurityTests(unittest.TestCase):
    def test_scanner_detects_private_keys_and_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "key.txt"
            key.write_text("-----BEGIN PRIVATE KEY-----\nsecret\n", encoding="utf-8")
            env = Path(tmp) / ".env"
            env.write_text("TOKEN=secret", encoding="utf-8")
            findings = scan_files([key, env])
        self.assertEqual({finding.rule for finding in findings}, {"private_key", "sensitive_file"})

    def test_body_limit_and_content_type_are_enforced(self) -> None:
        with self.assertRaises(SecurityRequestError) as too_large:
            validate_body_contract("/api/v1/admin/config", b"x" * (MAX_BODY_BYTES + 1), "application/json")
        with self.assertRaises(SecurityRequestError) as multipart:
            validate_body_contract("/api/v1/admin/config", b"payload", "multipart/form-data")
        self.assertEqual(too_large.exception.status, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(multipart.exception.status, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    def test_traversal_targets_are_rejected(self) -> None:
        for path in ("/api/../secret", "/api/%2e%2e/secret", "/api/%2Fetc"):
            with self.assertRaises(SecurityRequestError):
                validate_request_target(path)

    def test_rate_limiter_is_ephemeral_and_configurable(self) -> None:
        limiter = RateLimiter()
        env = {"MWANGAZA_RATE_LIMIT_REQUESTS": "2", "MWANGAZA_RATE_LIMIT_WINDOW_SECONDS": "10"}
        limiter.check("client", env=env, now=0)
        limiter.check("client", env=env, now=1)
        with self.assertRaises(SecurityRequestError) as limited:
            limiter.check("client", env=env, now=2)
        self.assertEqual(limited.exception.status, HTTPStatus.TOO_MANY_REQUESTS)
        limiter.check("client", env=env, now=11)

    def test_api_rejects_large_payload_and_returns_security_headers(self) -> None:
        RATE_LIMITER.reset()
        status, headers, payload = _request(
            "/api/v1/admin/config",
            body=b"x" * (MAX_BODY_BYTES + 1),
            headers=[(b"content-type", b"application/json")],
        )
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"]["code"], "payload_too_large")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["x-frame-options"], "DENY")
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])

    def test_api_rate_limit_returns_429_without_persisting_identity(self) -> None:
        RATE_LIMITER.reset()
        with patch.dict("os.environ", {"MWANGAZA_RATE_LIMIT_REQUESTS": "1"}, clear=False):
            first, _headers, _payload = _request("/api/v1/regions")
            second, _headers, payload = _request("/api/v1/regions")
        RATE_LIMITER.reset()
        self.assertEqual(first, 200)
        self.assertEqual(second, 429)
        self.assertEqual(payload["error"]["code"], "rate_limited")


def _request(
    path: str,
    *,
    body: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, str], dict[str, object]]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(app({
        "type": "http",
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": ("security-test", 1000),
    }, receive, send))
    start, response = messages
    response_headers = {key.decode("ascii"): value.decode("ascii") for key, value in start["headers"]}  # type: ignore[index]
    return int(start["status"]), response_headers, json.loads(response["body"])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

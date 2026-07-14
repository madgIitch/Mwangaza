from __future__ import annotations

import asyncio
import json
import unittest

import mwangaza
from mwangaza.api.app import app
from mwangaza.data.refresh import main


class FoundationTests(unittest.TestCase):
    def test_version_contract(self) -> None:
        self.assertEqual(mwangaza.__version__, "0.0.1")

    def test_refresh_dry_run_succeeds(self) -> None:
        self.assertEqual(main(["--dry-run"]), 0)

    def test_health_endpoint_is_stubbed(self) -> None:
        messages: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        asyncio.run(app({"type": "http", "path": "/health"}, receive, send))

        self.assertEqual(messages[0]["status"], 200)
        body = json.loads(messages[1]["body"])
        self.assertEqual(body["project"], "Mwangaza")
        self.assertEqual(body["status"], "foundation stub")
        self.assertFalse(body["remote_calls_enabled"])


if __name__ == "__main__":
    unittest.main()

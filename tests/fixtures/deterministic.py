from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

FIXED_NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def fixed_clock() -> datetime:
    return FIXED_NOW


@dataclass
class FakeEarthEngine:
    responses: list[Any]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def query(self, **request: Any) -> Any:
        self.calls.append(request)
        if not self.responses:
            raise RuntimeError("fake Earth Engine response queue exhausted")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@dataclass
class FakeNotifier:
    messages: list[dict[str, Any]] = field(default_factory=list)

    def send(self, payload: dict[str, Any]) -> str:
        self.messages.append(payload)
        return f"simulated-{len(self.messages):03d}"

from __future__ import annotations

import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Mapping

MAX_BODY_BYTES = 64 * 1024
SECURITY_HEADERS = {
    "content-security-policy": "default-src 'self'; img-src 'self' data: https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
}


class SecurityRequestError(ValueError):
    def __init__(self, code: str, message: str, status: HTTPStatus) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, client: str, *, env: Mapping[str, str] | None = None, now: float | None = None) -> None:
        source = env or os.environ
        limit = _positive_int(source.get("MWANGAZA_RATE_LIMIT_REQUESTS"), 120)
        window = _positive_int(source.get("MWANGAZA_RATE_LIMIT_WINDOW_SECONDS"), 60)
        current = time.monotonic() if now is None else now
        key = client or "unknown"
        with self._lock:
            events = self._events[key]
            while events and current - events[0] >= window:
                events.popleft()
            if len(events) >= limit:
                raise SecurityRequestError("rate_limited", "Request rate limit exceeded", HTTPStatus.TOO_MANY_REQUESTS)
            events.append(current)


RATE_LIMITER = RateLimiter()


def validate_request_target(path: str) -> None:
    lowered = path.lower()
    if ".." in path or "%2e" in lowered or "%2f" in lowered or "%5c" in lowered:
        raise SecurityRequestError("invalid_request", "Request path is invalid", HTTPStatus.BAD_REQUEST)


def validate_body_contract(path: str, body: bytes, content_type: str) -> None:
    if len(body) > MAX_BODY_BYTES:
        raise SecurityRequestError("payload_too_large", "Request body exceeds 64 KiB", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
    if not body:
        return
    if path not in {"/api/v1/admin/config", "/api/v1/admin/config/activate"}:
        raise SecurityRequestError("unsupported_media_type", "Request body is not supported for this endpoint", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise SecurityRequestError("unsupported_media_type", "Request body must use application/json", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)


@dataclass(frozen=True)
class ScanFinding:
    path: str
    rule: str


_CONTENT_RULES = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("gcp_service_account", re.compile(r'"type"\s*:\s*"service_account"')),
    ("gcp_private_key", re.compile(r'"private_key"\s*:\s*"-----BEGIN')),
)


def scan_files(paths: list[Path]) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for path in paths:
        normalized = path.as_posix()
        if path.name == ".env" or path.suffix.lower() in {".pem", ".p12", ".pfx"} or "credentials" in path.name.lower():
            findings.append(ScanFinding(normalized, "sensitive_file"))
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for rule, pattern in _CONTENT_RULES:
            if pattern.search(content):
                findings.append(ScanFinding(normalized, rule))
    return findings


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value or default)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


__all__ = ["MAX_BODY_BYTES", "RATE_LIMITER", "SECURITY_HEADERS", "RateLimiter", "ScanFinding", "SecurityRequestError", "scan_files", "validate_body_contract", "validate_request_target"]

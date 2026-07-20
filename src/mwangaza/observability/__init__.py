from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

RUN_ID_HEADER = "x-run-id"
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_SENSITIVE_PARTS = ("authorization", "credential", "password", "private_key", "secret", "token")
_current_run_id: ContextVar[str] = ContextVar("mwangaza_run_id", default="system")


def resolve_run_id(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate if _RUN_ID_PATTERN.fullmatch(candidate) else uuid4().hex


def bind_run_id(run_id: str) -> Token[str]:
    return _current_run_id.set(run_id)


def reset_run_id(token: Token[str]) -> None:
    _current_run_id.reset(token)


def current_run_id() -> str:
    return _current_run_id.get()


def redact(value: Any, *, env: Mapping[str, str] | None = None) -> Any:
    secrets = _known_secrets(env or os.environ)
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(str(key)) else redact(item, env=env)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(item, env=env) for item in value]
    if isinstance(value, Path):
        return "[LOCAL_PATH]"
    if isinstance(value, str):
        result = value
        for secret in secrets:
            result = result.replace(secret, "[REDACTED]")
        if _looks_like_local_path(result):
            return "[LOCAL_PATH]"
        return result
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return type(value).__name__


def structured_event(event: str, *, level: str = "INFO", component: str = "api", run_id: str | None = None, **fields: Any) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper(),
        "component": component,
        "event": event,
        "run_id": run_id or current_run_id(),
        **redact(fields),
    }


def emit(event: str, *, level: str = "INFO", component: str = "api", run_id: str | None = None, **fields: Any) -> None:
    try:
        print(json.dumps(structured_event(event, level=level, component=component, run_id=run_id, **fields), sort_keys=True), flush=True)
    except Exception:
        return


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", threading.Lock()):
            self._requests = 0
            self._duration_ms = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._regions_processed = 0
            self._errors = 0
            self._active_alerts = 0

    def record_request(self, duration_ms: int, *, error: bool = False) -> None:
        with self._lock:
            self._requests += 1
            self._duration_ms += max(0, duration_ms)
            self._errors += int(error)

    def record_error(self) -> None:
        with self._lock:
            self._errors += 1

    def record_cache(self, hit: bool) -> None:
        with self._lock:
            self._cache_hits += int(hit)
            self._cache_misses += int(not hit)

    def observe_workload(self, *, regions_processed: int | None = None, active_alerts: int | None = None) -> None:
        with self._lock:
            if regions_processed is not None:
                self._regions_processed += max(0, regions_processed)
            if active_alerts is not None:
                self._active_alerts = max(0, active_alerts)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            requests = self._requests
            cache_total = self._cache_hits + self._cache_misses
            return {
                "requests_total": requests,
                "duration_ms_total": self._duration_ms,
                "duration_ms_average": round(self._duration_ms / requests, 2) if requests else 0,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_ratio": round(self._cache_hits / cache_total, 3) if cache_total else 0,
                "regions_processed": self._regions_processed,
                "errors_total": self._errors,
                "active_alerts": self._active_alerts,
            }


METRICS = MetricsRegistry()


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]

    def to_public_dict(self) -> dict[str, Any]:
        return {"status": "ready" if self.ready else "not_ready", "ready": self.ready, "checks": self.checks}


def readiness_status(env: Mapping[str, str] | None = None) -> ReadinessResult:
    source = env or os.environ
    checks: dict[str, str] = {}
    db_path = Path(source.get("MWANGAZA_ADMIN_DB", ".cache/mwangaza/admin.sqlite"))
    checks["database"] = _database_check(db_path)
    if source.get("MWANGAZA_CACHE_REQUIRED", "false").lower() in {"1", "true", "yes"}:
        cache_path = Path(source.get("MWANGAZA_CACHE_DIR", ".cache/mwangaza"))
        checks["cache"] = "ok" if cache_path.is_dir() and os.access(cache_path, os.R_OK | os.W_OK) else "unavailable"
    else:
        checks["cache"] = "optional"
    return ReadinessResult(all(value in {"ok", "optional"} for value in checks.values()), checks)


def _database_check(path: Path) -> str:
    try:
        if not path.parent.is_dir() or not os.access(path.parent, os.W_OK):
            return "unavailable"
        connection = sqlite3.connect(f"file:{path}?mode=rwc", uri=True, timeout=0.2)
        connection.execute("SELECT 1").fetchone()
        connection.close()
        return "ok"
    except (OSError, sqlite3.Error):
        return "unavailable"


def _known_secrets(env: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(value for key, value in env.items() if value and len(value) >= 6 and _is_sensitive_key(key))


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_PARTS)


def _looks_like_local_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", value) or value.startswith(("/home/", "/Users/")))


__all__ = ["METRICS", "RUN_ID_HEADER", "ReadinessResult", "bind_run_id", "current_run_id", "emit", "readiness_status", "redact", "reset_run_id", "resolve_run_id", "structured_event"]

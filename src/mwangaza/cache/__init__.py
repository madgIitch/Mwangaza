from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

SENSITIVE_KEY_PARTS = ("private_key", "service_account", "token", "secret", "password")


class CacheError(ValueError):
    pass


@dataclass(frozen=True)
class CacheKey:
    region_id: str
    indicator: str
    period_start: str
    period_end: str
    source: str
    algorithm_version: str
    data_type: str

    @property
    def digest(self) -> str:
        return sha256(_stable_json(asdict(self)).encode()).hexdigest()

    @property
    def filename(self) -> str:
        return f"{self.digest}.json"


@dataclass(frozen=True)
class CacheEntry:
    cache_key: str
    algorithm_version: str
    created_at: str
    expires_at: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return _parse_datetime(self.expires_at, "expires_at") <= current

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CacheConfig:
    cache_dir: Path
    ttl_by_data_type: Mapping[str, int] = field(default_factory=lambda: {"default": 3600})

    def ttl_seconds(self, data_type: str) -> int:
        ttl = self.ttl_by_data_type.get(data_type, self.ttl_by_data_type.get("default", 3600))
        if ttl <= 0:
            raise CacheError("ttl_seconds must be positive")
        return int(ttl)


def build_cache_key(
    *,
    region_id: str,
    indicator: str,
    period_start: str,
    period_end: str,
    source: str,
    algorithm_version: str,
    data_type: str,
) -> CacheKey:
    values = {
        "region_id": region_id.strip().lower(),
        "indicator": indicator.strip(),
        "period_start": period_start.strip(),
        "period_end": period_end.strip(),
        "source": source.strip(),
        "algorithm_version": algorithm_version.strip(),
        "data_type": data_type.strip(),
    }
    if any(not value for value in values.values()):
        raise CacheError("cache key fields are required")
    return CacheKey(**values)


class AnalyticalCache:
    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_status = "miss"

    def get_or_compute(
        self,
        key: CacheKey,
        producer: Callable[[], dict[str, Any]],
        *,
        now: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        entry = self.read(key, now=now)
        if entry is not None:
            self.last_status = "hit"
            return entry

        payload = producer()
        entry = self.write(key, payload, now=now, metadata=metadata)
        self.last_status = "miss"
        return entry

    def read(self, key: CacheKey, *, now: datetime | None = None) -> CacheEntry | None:
        path = self._path_for(key)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entry = CacheEntry(
                cache_key=_required_str(raw, "cache_key"),
                algorithm_version=_required_str(raw, "algorithm_version"),
                created_at=_required_str(raw, "created_at"),
                expires_at=_required_str(raw, "expires_at"),
                payload=_required_dict(raw, "payload"),
                metadata=_metadata(raw),
            )
        except (OSError, json.JSONDecodeError, CacheError):
            self.last_status = "corrupt" if path.exists() else "miss"
            return None
        if entry.cache_key != key.digest or entry.algorithm_version != key.algorithm_version:
            self.last_status = "miss"
            return None
        if entry.is_expired(now):
            self.last_status = "expired"
            return None
        self.last_status = "hit"
        return entry

    def write(
        self,
        key: CacheKey,
        payload: dict[str, Any],
        *,
        now: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        _reject_sensitive(payload)
        _reject_sensitive(metadata or {})
        _assert_json_serializable(payload)
        created = now or datetime.now(UTC)
        ttl = self.config.ttl_seconds(key.data_type)
        entry = CacheEntry(
            cache_key=key.digest,
            algorithm_version=key.algorithm_version,
            created_at=_format_datetime(created),
            expires_at=_format_datetime(created + timedelta(seconds=ttl)),
            payload=dict(payload),
            metadata={
                "data_type": key.data_type,
                "status": "stored",
                **(metadata or {}),
            },
        )
        path = self._path_for(key)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(_stable_json(entry.to_dict()), encoding="utf-8")
        os.replace(tmp_path, path)
        return entry

    def _path_for(self, key: CacheKey) -> Path:
        return self.config.cache_dir / key.filename


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _reject_sensitive(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                raise CacheError(f"cache payload contains sensitive field: {path}{key}")
            _reject_sensitive(item, f"{path}{key}.")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_sensitive(item, f"{path}{index}.")


def _assert_json_serializable(payload: dict[str, Any]) -> None:
    try:
        _stable_json(payload)
    except (TypeError, ValueError) as exc:
        raise CacheError("cache payload must be JSON serializable") from exc


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CacheError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise CacheError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _required_str(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise CacheError(f"{field_name} is required")
    return value


def _required_dict(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise CacheError(f"{field_name} must be an object")
    return value


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("metadata", {})
    if not isinstance(value, dict):
        raise CacheError("metadata must be an object")
    return value


__all__ = [
    "AnalyticalCache",
    "CacheConfig",
    "CacheEntry",
    "CacheError",
    "CacheKey",
    "build_cache_key",
]

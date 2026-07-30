from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence
from uuid import uuid4

REFRESH_SCHEMA_VERSION = "mwangaza.scheduled-refresh.v1"
DEFAULT_STALE_AFTER_DAYS = 21
DEFAULT_LOCK_TTL_MINUTES = 180


class ScheduledRefreshError(RuntimeError):
    pass


class RefreshLockUnavailable(ScheduledRefreshError):
    pass


@dataclass(frozen=True)
class RefreshRunResult:
    run_id: str
    period: str
    status: str
    started_at: str
    finished_at: str
    snapshot_path: str | None
    quality_summary: dict[str, Any]
    message: str

    @property
    def exit_code(self) -> int:
        return 0 if self.status in {"published", "skipped"} else 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"exit_code": self.exit_code}


class FileRefreshStore:
    """Atomic local store; production can mount the same layout from Cloud Storage."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.lock_dir = root / ".refresh-locks"
        self.snapshot_dir = root / "refresh-snapshots"
        self.status_path = root / "refresh-status.json"
        self.latest_path = root / "live-dashboard-last-good.json"

    def acquire_lock(
        self,
        period: str,
        run_id: str,
        *,
        now: datetime,
        ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES,
    ) -> Path:
        lock_path = self.lock_dir / "active.lock.json"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "period": period,
            "owner_run_id": run_id,
            "acquired_at": _iso(now),
            "expires_at": _iso(now + timedelta(minutes=ttl_minutes)),
        }
        for _attempt in range(2):
            try:
                descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                existing = _read_json(lock_path)
                expires_at = _parse_time(existing.get("expires_at")) if existing else None
                if expires_at is not None and expires_at <= now:
                    try:
                        lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                owner = str(existing.get("owner_run_id", "unknown")) if existing else "unknown"
                raise RefreshLockUnavailable(f"period {period} is locked by run {owner}")
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            return lock_path
        raise RefreshLockUnavailable(f"could not acquire lock for period {period}")

    def release_lock(self, lock_path: Path, run_id: str) -> None:
        payload = _read_json(lock_path)
        if payload and payload.get("owner_run_id") != run_id:
            raise ScheduledRefreshError("refusing to release a lock owned by another run")
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass

    def read_status(self) -> dict[str, Any]:
        return _read_json(self.status_path)

    def publish(
        self,
        payloads: Sequence[dict[str, Any]],
        *,
        run_id: str,
        period: str,
        started_at: str,
        finished_at: str,
        query_generated_at: str,
        quality_summary: dict[str, Any],
        stale_after_days: int,
    ) -> Path:
        effective_at = str(quality_summary["effective_observation_at"])
        age_days = _age_days(effective_at, finished_at)
        snapshot = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "refresh": {
                "run_id": run_id,
                "period": period,
                "status": "published",
                "started_at": started_at,
                "finished_at": finished_at,
                "query_generated_at": query_generated_at,
                "effective_observation_at": effective_at,
                "age_days": age_days,
                "freshness": "stale" if age_days > stale_after_days else "current",
                "stale_after_days": stale_after_days,
                "quality_summary": quality_summary,
            },
            "payload": list(payloads),
        }
        _validate_snapshot(snapshot)
        immutable = self.snapshot_dir / _safe_segment(period) / f"{_safe_segment(run_id)}.json"
        immutable.parent.mkdir(parents=True, exist_ok=True)
        _write_immutable(immutable, snapshot)
        _atomic_write(self.latest_path, snapshot)
        previous = self.read_status()
        status = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "state": snapshot["refresh"]["freshness"],
            "last_attempt": snapshot["refresh"],
            "last_success": snapshot["refresh"] | {"snapshot_path": str(immutable)},
            "previous_success": previous.get("last_success"),
        }
        _atomic_write(self.status_path, status)
        return immutable

    def record_failure(
        self,
        *,
        run_id: str,
        period: str,
        started_at: str,
        finished_at: str,
        message: str,
    ) -> None:
        previous = self.read_status()
        status = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "state": "failed",
            "last_attempt": {
                "run_id": run_id,
                "period": period,
                "status": "failed",
                "started_at": started_at,
                "finished_at": finished_at,
                "message": _sanitize_message(message),
            },
            "last_success": previous.get("last_success"),
        }
        _atomic_write(self.status_path, status)


class RefreshStore(Protocol):
    def acquire_lock(
        self, period: str, run_id: str, *, now: datetime, ttl_minutes: int
    ) -> Any: ...

    def release_lock(self, lock_handle: Any, run_id: str) -> None: ...

    def read_status(self) -> dict[str, Any]: ...

    def publish(self, payloads: Sequence[dict[str, Any]], **kwargs: Any) -> Any: ...

    def record_failure(self, **kwargs: Any) -> None: ...


class GcsRefreshStore:
    """Generation-guarded Cloud Storage store used by the production Job."""

    def __init__(self, bucket_name: str, *, prefix: str = "mwangaza-refresh", client: Any = None) -> None:
        if not bucket_name.strip():
            raise ScheduledRefreshError("GCS bucket name is required")
        if client is None:
            from google.cloud import storage

            client = storage.Client()
        self.bucket = client.bucket(bucket_name)
        self.prefix = prefix.strip("/")

    def _name(self, suffix: str) -> str:
        return f"{self.prefix}/{suffix.lstrip('/')}"

    def acquire_lock(
        self,
        period: str,
        run_id: str,
        *,
        now: datetime,
        ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES,
    ) -> str:
        from google.api_core.exceptions import NotFound, PreconditionFailed

        name = self._name("locks/active.json")
        payload = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "period": period,
            "owner_run_id": run_id,
            "acquired_at": _iso(now),
            "expires_at": _iso(now + timedelta(minutes=ttl_minutes)),
        }
        for _attempt in range(2):
            blob = self.bucket.blob(name)
            try:
                blob.upload_from_string(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    content_type="application/json",
                    if_generation_match=0,
                )
                return name
            except PreconditionFailed:
                existing = self._read_blob(name)
                expires_at = _parse_time(existing.get("expires_at")) if existing else None
                if expires_at is not None and expires_at <= now:
                    try:
                        current = self.bucket.get_blob(name)
                        if current is not None:
                            current.delete(if_generation_match=current.generation)
                    except (NotFound, PreconditionFailed):
                        pass
                    continue
                owner = str(existing.get("owner_run_id", "unknown")) if existing else "unknown"
                raise RefreshLockUnavailable(f"period {period} is locked by run {owner}")
        raise RefreshLockUnavailable(f"could not acquire lock for period {period}")

    def release_lock(self, lock_handle: str, run_id: str) -> None:
        from google.api_core.exceptions import NotFound, PreconditionFailed

        payload = self._read_blob(lock_handle)
        if payload and payload.get("owner_run_id") != run_id:
            raise ScheduledRefreshError("refusing to release a lock owned by another run")
        blob = self.bucket.get_blob(lock_handle)
        if blob is None:
            return
        try:
            blob.delete(if_generation_match=blob.generation)
        except (NotFound, PreconditionFailed):
            return

    def read_status(self) -> dict[str, Any]:
        return self._read_blob(self._name("refresh-status.json"))

    def publish(
        self,
        payloads: Sequence[dict[str, Any]],
        *,
        run_id: str,
        period: str,
        started_at: str,
        finished_at: str,
        query_generated_at: str,
        quality_summary: dict[str, Any],
        stale_after_days: int,
    ) -> str:
        effective_at = str(quality_summary["effective_observation_at"])
        age_days = _age_days(effective_at, finished_at)
        refresh = {
            "run_id": run_id,
            "period": period,
            "status": "published",
            "started_at": started_at,
            "finished_at": finished_at,
            "query_generated_at": query_generated_at,
            "effective_observation_at": effective_at,
            "age_days": age_days,
            "freshness": "stale" if age_days > stale_after_days else "current",
            "stale_after_days": stale_after_days,
            "quality_summary": quality_summary,
        }
        snapshot = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "refresh": refresh,
            "payload": list(payloads),
        }
        _validate_snapshot(snapshot)
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        immutable_name = self._name(
            f"snapshots/{_safe_segment(period)}/{_safe_segment(run_id)}.json"
        )
        self.bucket.blob(immutable_name).upload_from_string(
            encoded, content_type="application/json", if_generation_match=0
        )
        self.bucket.blob(self._name("live-dashboard-last-good.json")).upload_from_string(
            encoded, content_type="application/json"
        )
        previous = self.read_status()
        status = {
            "schema_version": REFRESH_SCHEMA_VERSION,
            "state": refresh["freshness"],
            "last_attempt": refresh,
            "last_success": refresh | {"snapshot_path": f"gs://{self.bucket.name}/{immutable_name}"},
            "previous_success": previous.get("last_success"),
        }
        self._write_status(status)
        return f"gs://{self.bucket.name}/{immutable_name}"

    def record_failure(
        self,
        *,
        run_id: str,
        period: str,
        started_at: str,
        finished_at: str,
        message: str,
    ) -> None:
        previous = self.read_status()
        self._write_status(
            {
                "schema_version": REFRESH_SCHEMA_VERSION,
                "state": "failed",
                "last_attempt": {
                    "run_id": run_id,
                    "period": period,
                    "status": "failed",
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "message": _sanitize_message(message),
                },
                "last_success": previous.get("last_success"),
            }
        )

    def _write_status(self, payload: dict[str, Any]) -> None:
        self.bucket.blob(self._name("refresh-status.json")).upload_from_string(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            content_type="application/json",
        )

    def _read_blob(self, name: str) -> dict[str, Any]:
        from google.api_core.exceptions import NotFound

        try:
            value = json.loads(self.bucket.blob(name).download_as_text())
        except (NotFound, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}


PayloadProvider = Callable[[], Sequence[dict[str, Any]]]


def run_scheduled_refresh(
    provider: PayloadProvider,
    store: RefreshStore,
    *,
    period: str,
    run_id: str | None = None,
    now: Callable[[], datetime] | None = None,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    lock_ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES,
) -> RefreshRunResult:
    _validate_period(period)
    if stale_after_days < 1:
        raise ScheduledRefreshError("stale_after_days must be positive")
    resolved_run_id = run_id or uuid4().hex
    clock = now or (lambda: datetime.now(UTC))
    started = clock()
    started_at = _iso(started)
    lock_path: Any = None
    try:
        lock_path = store.acquire_lock(
            period,
            resolved_run_id,
            now=started,
            ttl_minutes=lock_ttl_minutes,
        )
        last_success = store.read_status().get("last_success") or {}
        if last_success.get("period") == period and last_success.get("status") == "published":
            finished_at = _iso(clock())
            return RefreshRunResult(
                resolved_run_id,
                period,
                "skipped",
                started_at,
                finished_at,
                str(last_success.get("snapshot_path") or "") or None,
                dict(last_success.get("quality_summary") or {}),
                "period already published",
            )
        payloads = tuple(provider())
        quality = summarize_payload_quality(payloads)
        finished_at = _iso(clock())
        snapshot_path = store.publish(
            payloads,
            run_id=resolved_run_id,
            period=period,
            started_at=started_at,
            finished_at=finished_at,
            query_generated_at=finished_at,
            quality_summary=quality,
            stale_after_days=stale_after_days,
        )
        return RefreshRunResult(
            resolved_run_id,
            period,
            "published",
            started_at,
            finished_at,
            str(snapshot_path),
            quality,
            "snapshot published atomically",
        )
    except RefreshLockUnavailable as exc:
        finished_at = _iso(clock())
        return RefreshRunResult(
            resolved_run_id, period, "skipped", started_at, finished_at, None, {}, str(exc)
        )
    except Exception as exc:  # noqa: BLE001 - failure must preserve and report last-known-good.
        finished_at = _iso(clock())
        store.record_failure(
            run_id=resolved_run_id,
            period=period,
            started_at=started_at,
            finished_at=finished_at,
            message=str(exc),
        )
        return RefreshRunResult(
            resolved_run_id,
            period,
            "failed",
            started_at,
            finished_at,
            None,
            {},
            _sanitize_message(str(exc)),
        )
    finally:
        if lock_path is not None:
            store.release_lock(lock_path, resolved_run_id)


def summarize_payload_quality(payloads: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        raise ScheduledRefreshError("refresh returned no payloads")
    observation_times = [
        str(value)
        for payload in payloads
        for value in (payload.get("period_end"), payload.get("newest_updated_at"))
        if value
    ]
    if not observation_times:
        raise ScheduledRefreshError("payloads do not expose an effective observation date")
    real_payloads = [
        payload
        for payload in payloads
        if isinstance(payload.get("metadata"), dict)
        and payload["metadata"].get("smoke_source") == "real_gee"
    ]
    if not real_payloads:
        raise ScheduledRefreshError("payload batch is not verified as real GEE evidence")
    region_ids = {str(payload.get("region_id")) for payload in payloads if payload.get("region_id")}
    error_count = sum(1 for payload in payloads if payload.get("status") == "error")
    return {
        "payload_count": len(payloads),
        "verified_real_gee_count": len(real_payloads),
        "region_count": len(region_ids),
        "error_count": error_count,
        "effective_observation_at": max(observation_times),
    }


def load_refresh_status(
    cache_dir: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    status = _read_json(cache_dir / "refresh-status.json")
    if status:
        result = json.loads(json.dumps(status))
        success = result.get("last_success")
        if isinstance(success, dict) and success.get("effective_observation_at"):
            age_days = _age_days(
                str(success["effective_observation_at"]),
                _iso(now or datetime.now(UTC)),
            )
            success["age_days"] = age_days
            stale_after = int(success.get("stale_after_days", DEFAULT_STALE_AFTER_DAYS))
            success["freshness"] = "stale" if age_days > stale_after else "current"
            if result.get("state") != "failed":
                result["state"] = success["freshness"]
        return result
    return {
        "schema_version": REFRESH_SCHEMA_VERSION,
        "state": "unavailable",
        "last_attempt": None,
        "last_success": None,
    }


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema_version") != REFRESH_SCHEMA_VERSION:
        raise ScheduledRefreshError("invalid snapshot schema")
    if not isinstance(snapshot.get("payload"), list) or not snapshot["payload"]:
        raise ScheduledRefreshError("snapshot payload must be a non-empty list")
    refresh = snapshot.get("refresh")
    if not isinstance(refresh, dict) or not refresh.get("run_id"):
        raise ScheduledRefreshError("snapshot refresh metadata is incomplete")


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temp.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _write_immutable(path: Path, payload: dict[str, Any]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _validate_period(period: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
        raise ScheduledRefreshError("period must be YYYY-MM-DD")
    try:
        datetime.strptime(period, "%Y-%m-%d")
    except ValueError as exc:
        raise ScheduledRefreshError("period must be a valid date") from exc


def _safe_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)[:120]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC)


def _age_days(observed_at: str, compared_at: str) -> int:
    observed = _parse_time(observed_at[:10] + "T00:00:00Z" if len(observed_at) == 10 else observed_at)
    compared = _parse_time(compared_at)
    if observed is None or compared is None:
        raise ScheduledRefreshError("invalid freshness timestamps")
    return max(0, (compared - observed).days)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sanitize_message(value: str) -> str:
    compact = " ".join(value.split())
    compact = re.sub(r"(?i)(private[_ -]?key|token|secret|password)\s*[:=]\s*\S+", r"\1=[redacted]", compact)
    return compact[:500]


__all__ = [
    "FileRefreshStore",
    "GcsRefreshStore",
    "RefreshLockUnavailable",
    "RefreshRunResult",
    "ScheduledRefreshError",
    "load_refresh_status",
    "run_scheduled_refresh",
    "summarize_payload_quality",
]

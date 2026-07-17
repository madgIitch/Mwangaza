from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SENSITIVE = ("secret", "token", "private_key", "credential", "password")
MAX_LIMIT = 500


@dataclass(frozen=True)
class AuditEvent:
    event_id: int
    actor: str
    event_type: str
    entity_type: str
    entity_id: str
    region_id: str
    timestamp: str
    run_id: str
    snapshot_id: str
    model_version: str
    metadata: dict[str, Any]


class AuditRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self.migrate()

    def close(self) -> None:
        self._conn.close()

    def migrate(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                region_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                run_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def record_event(
        self,
        *,
        actor: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        region_id: str = "",
        run_id: str = "",
        snapshot_id: str = "",
        model_version: str = "",
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditEvent:
        ts = (timestamp or datetime.now(UTC)).replace(microsecond=0).isoformat()
        clean = _redact(metadata or {})
        cur = self._conn.execute(
            """
            INSERT INTO audit_events(actor,event_type,entity_type,entity_id,region_id,timestamp,
            run_id,snapshot_id,model_version,metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor,
                event_type,
                entity_type,
                entity_id,
                region_id,
                ts,
                run_id,
                snapshot_id,
                model_version,
                json.dumps(clean, sort_keys=True),
            ),
        )
        self._conn.commit()
        return self.get_event(int(cur.lastrowid))

    def record_alert_event(
        self,
        *,
        actor: str,
        event_type: str,
        alert_id: str,
        region_id: str,
        run_id: str,
        snapshot_id: str,
        model_version: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        if event_type not in {"alert_created", "alert_escalated", "alert_deescalated", "alert_resolved"}:
            raise ValueError("unsupported alert audit event")
        return self.record_event(
            actor=actor,
            event_type=event_type,
            entity_type="alert",
            entity_id=alert_id,
            region_id=region_id,
            run_id=run_id,
            snapshot_id=snapshot_id,
            model_version=model_version,
            metadata=metadata,
        )

    def record_config_change(
        self,
        *,
        actor: str,
        entity_id: str,
        previous_version: dict[str, Any],
        new_version: dict[str, Any],
        run_id: str = "",
    ) -> AuditEvent:
        return self.record_event(
            actor=actor,
            event_type="configuration_changed",
            entity_type="configuration",
            entity_id=entity_id,
            run_id=run_id,
            metadata={"previous_version": previous_version, "new_version": new_version},
        )

    def get_event(self, event_id: int) -> AuditEvent:
        row = self._conn.execute("SELECT * FROM audit_events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown audit event: {event_id}")
        return _event(row)

    def list_events(
        self,
        *,
        region_id: str | None = None,
        run_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> tuple[AuditEvent, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        clauses: list[str] = []
        params: list[Any] = []
        if region_id is not None:
            clauses.append("region_id=?")
            params.append(region_id)
        if run_id is not None:
            clauses.append("run_id=?")
            params.append(run_id)
        if event_type is not None:
            clauses.append("event_type=?")
            params.append(event_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM audit_events{where} ORDER BY id LIMIT ?",
            (*params, min(limit, MAX_LIMIT)),
        ).fetchall()
        return tuple(_event(row) for row in rows)


def _event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=int(row["id"]),
        actor=row["actor"],
        event_type=row["event_type"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        region_id=row["region_id"],
        timestamp=row["timestamp"],
        run_id=row["run_id"],
        snapshot_id=row["snapshot_id"],
        model_version=row["model_version"],
        metadata=json.loads(row["metadata_json"]),
    )


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[redacted]" if _sensitive(key) else _redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        if _sensitive(value) or "\\" in value or re.search(r"[A-Za-z]:/", value.replace("\\", "/")):
            return "[redacted]"
        return value
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


def _sensitive(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SENSITIVE)


__all__ = ["AuditEvent", "AuditRepository"]

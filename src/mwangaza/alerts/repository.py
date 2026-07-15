from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mwangaza.actions import ActionRecommendation
from mwangaza.contracts import RiskSnapshot


class AlertRepositoryError(ValueError):
    pass


@dataclass(frozen=True)
class StoredAlert:
    alert_id: int
    region_id: str
    alert_type: str
    period_start: str
    period_end: str
    model_version: str
    severity: str
    status: str
    score: float | None
    quality_flag: str
    evidence: dict[str, Any]
    recommendations: tuple[dict[str, Any], ...]


class AlertRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                model_version TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL,
                quality_flag TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                UNIQUE(region_id, alert_type, period_start, period_end, model_version)
            );
            CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                from_severity TEXT,
                to_severity TEXT,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._conn.commit()

    def upsert_alert(
        self,
        risk_snapshot: RiskSnapshot,
        recommendations: tuple[ActionRecommendation, ...],
        *,
        alert_type: str = "drought",
        model_version: str | None = None,
    ) -> StoredAlert:
        self.migrate()
        version = model_version or str(risk_snapshot.metadata.get("model_version", "unknown-model"))
        if not all([risk_snapshot.region_id, alert_type, risk_snapshot.period_start, risk_snapshot.period_end, version]):
            raise AlertRepositoryError("alert identity fields are required")
        evidence = dict(risk_snapshot.metadata)
        rec_payload = tuple(item.to_dict() for item in recommendations)
        _assert_json(evidence)
        _assert_json(rec_payload)
        existing = self._find(risk_snapshot.region_id, alert_type, risk_snapshot.period_start, risk_snapshot.period_end, version)
        severity = risk_snapshot.risk_level
        if existing is None:
            cur = self._conn.execute(
                """
                INSERT INTO alerts(region_id, alert_type, period_start, period_end, model_version,
                severity, status, score, quality_flag, evidence_json, recommendations_json)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                """,
                (
                    risk_snapshot.region_id,
                    alert_type,
                    risk_snapshot.period_start,
                    risk_snapshot.period_end,
                    version,
                    severity,
                    risk_snapshot.composite_score,
                    risk_snapshot.quality_flag,
                    json.dumps(evidence, sort_keys=True),
                    json.dumps(rec_payload, sort_keys=True),
                ),
            )
            alert_id = int(cur.lastrowid)
            self._event(alert_id, "created", None, severity, "active", {})
        else:
            alert_id = int(existing["id"])
            if existing["severity"] != severity:
                self._event(alert_id, "severity_changed", existing["severity"], severity, existing["status"], {})
            self._conn.execute(
                """
                UPDATE alerts SET severity=?, score=?, quality_flag=?, evidence_json=?,
                recommendations_json=? WHERE id=?
                """,
                (
                    severity,
                    risk_snapshot.composite_score,
                    risk_snapshot.quality_flag,
                    json.dumps(evidence, sort_keys=True),
                    json.dumps(rec_payload, sort_keys=True),
                    alert_id,
                ),
            )
        self._conn.commit()
        return self.get_alert(alert_id)

    def resolve_alert(self, alert_id: int, *, reason: str = "resolved") -> StoredAlert:
        row = self._conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        if row is None:
            raise AlertRepositoryError(f"unknown alert_id: {alert_id}")
        self._conn.execute("UPDATE alerts SET status='resolved' WHERE id=?", (alert_id,))
        self._event(alert_id, "resolved", row["severity"], row["severity"], "resolved", {"reason": reason})
        self._conn.commit()
        return self.get_alert(alert_id)

    def get_alert(self, alert_id: int) -> StoredAlert:
        row = self._conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
        if row is None:
            raise AlertRepositoryError(f"unknown alert_id: {alert_id}")
        return _stored_alert(row)

    def list_events(self, alert_id: int) -> tuple[dict[str, Any], ...]:
        rows = self._conn.execute(
            "SELECT * FROM alert_events WHERE alert_id=? ORDER BY id",
            (alert_id,),
        ).fetchall()
        return tuple(
            {
                "event_type": row["event_type"],
                "from_severity": row["from_severity"],
                "to_severity": row["to_severity"],
                "status": row["status"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        )

    def _find(self, region_id: str, alert_type: str, period_start: str, period_end: str, model_version: str):
        return self._conn.execute(
            """
            SELECT * FROM alerts WHERE region_id=? AND alert_type=? AND period_start=?
            AND period_end=? AND model_version=?
            """,
            (region_id, alert_type, period_start, period_end, model_version),
        ).fetchone()

    def _event(
        self,
        alert_id: int,
        event_type: str,
        from_severity: str | None,
        to_severity: str | None,
        status: str,
        metadata: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO alert_events(alert_id, event_type, from_severity, to_severity, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (alert_id, event_type, from_severity, to_severity, status, json.dumps(metadata, sort_keys=True)),
        )


def _stored_alert(row: sqlite3.Row) -> StoredAlert:
    return StoredAlert(
        alert_id=int(row["id"]),
        region_id=row["region_id"],
        alert_type=row["alert_type"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        model_version=row["model_version"],
        severity=row["severity"],
        status=row["status"],
        score=row["score"],
        quality_flag=row["quality_flag"],
        evidence=json.loads(row["evidence_json"]),
        recommendations=tuple(json.loads(row["recommendations_json"])),
    )


def _assert_json(value: Any) -> None:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise AlertRepositoryError("alert payload must be JSON serializable") from exc


__all__ = ["AlertRepository", "AlertRepositoryError", "StoredAlert"]

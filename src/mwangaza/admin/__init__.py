from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mwangaza.actions import default_action_catalog
from mwangaza.alerts.thresholds import default_threshold_preset
from mwangaza.audit import AuditRepository

SCHEMA_VERSION = "mwangaza.admin.v1"


class AdminValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("configuration is invalid")
        self.errors = errors


@dataclass(frozen=True)
class ConfigurationVersion:
    version_id: str
    created_at: str
    created_by: str
    status: str
    content_hash: str
    configuration: dict[str, Any]
    validation_errors: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "status": self.status,
            "content_hash": self.content_hash,
            "configuration": self.configuration,
            "validation_errors": list(self.validation_errors),
        }


class AdminConfigurationRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self.audit = AuditRepository(self.path)
        self.migrate()

    def close(self) -> None:
        self.audit.close()
        self._conn.close()

    def migrate(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_config_versions (
                version_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                configuration_json TEXT NOT NULL,
                validation_errors_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
        if self.get_active() is None and not self.list_versions():
            self.create_version(default_admin_configuration(), actor="system", activate=True)

    def list_versions(self) -> tuple[ConfigurationVersion, ...]:
        rows = self._conn.execute(
            "SELECT * FROM admin_config_versions ORDER BY created_at DESC, version_id DESC"
        ).fetchall()
        return tuple(_version(row) for row in rows)

    def get_active(self) -> ConfigurationVersion | None:
        row = self._conn.execute(
            "SELECT * FROM admin_config_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return _version(row) if row is not None else None

    def get_version(self, version_id: str) -> ConfigurationVersion:
        row = self._conn.execute("SELECT * FROM admin_config_versions WHERE version_id=?", (version_id,)).fetchone()
        if row is None:
            raise ValueError("unknown configuration version")
        return _version(row)

    def create_version(self, configuration: dict[str, Any], *, actor: str, activate: bool = False) -> ConfigurationVersion:
        errors = validate_admin_configuration(configuration)
        status = "rejected" if errors else ("active" if activate else "draft")
        if activate and errors:
            raise AdminValidationError(errors)
        if activate:
            self._conn.execute("UPDATE admin_config_versions SET status='superseded' WHERE status='active'")
        created_at = _now()
        content_hash = _content_hash(configuration)
        version_id = f"cfg-{created_at.replace(':', '').replace('-', '').replace('+00:00', 'Z')}-{content_hash[:10]}"
        self._conn.execute(
            """
            INSERT INTO admin_config_versions(version_id, created_at, created_by, status, content_hash,
            configuration_json, validation_errors_json) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                created_at,
                actor,
                status,
                content_hash,
                json.dumps(configuration, sort_keys=True),
                json.dumps(errors, sort_keys=True),
            ),
        )
        self._conn.commit()
        version = self.get_version(version_id)
        self._audit(actor=actor, action="configuration_saved", version=version)
        if status == "active":
            self._audit(actor=actor, action="configuration_activated", version=version)
        return version

    def activate_version(self, version_id: str, *, actor: str) -> ConfigurationVersion:
        version = self.get_version(version_id)
        if version.validation_errors:
            raise AdminValidationError(list(version.validation_errors))
        self._conn.execute("UPDATE admin_config_versions SET status='superseded' WHERE status='active'")
        self._conn.execute("UPDATE admin_config_versions SET status='active' WHERE version_id=?", (version_id,))
        self._conn.commit()
        active = self.get_version(version_id)
        self._audit(actor=actor, action="configuration_activated", version=active)
        return active

    def _audit(self, *, actor: str, action: str, version: ConfigurationVersion) -> None:
        self.audit.record_event(
            actor=actor,
            event_type=action,
            entity_type="admin_configuration",
            entity_id=version.version_id,
            metadata={
                "status": version.status,
                "content_hash_prefix": version.content_hash[:12],
                "validation_error_count": len(version.validation_errors),
            },
        )


def admin_repository_from_env() -> AdminConfigurationRepository:
    path = os.environ.get("MWANGAZA_ADMIN_DB", ".cache/mwangaza/admin.sqlite")
    return AdminConfigurationRepository(path)


def default_admin_configuration() -> dict[str, Any]:
    thresholds = default_threshold_preset()
    actions = default_action_catalog()
    return {
        "schema_version": SCHEMA_VERSION,
        "thresholds": {
            "threshold_version": thresholds.threshold_version,
            "domain_min": thresholds.domain_min,
            "domain_max": thresholds.domain_max,
            "bands": [
                {"level": band.level, "minimum": band.minimum, "maximum": band.maximum}
                for band in thresholds.bands
            ],
            "is_official": thresholds.is_official,
            "label": thresholds.label,
        },
        "actions": {
            "recommendation_version": actions.recommendation_version,
            "templates": {
                level: {
                    "level": template.level,
                    "action": template.action,
                    "suggested_actor": template.suggested_actor,
                    "urgency": template.urgency,
                }
                for level, template in actions.templates.items()
            },
        },
    }


def validate_admin_configuration(configuration: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if configuration.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be mwangaza.admin.v1")
    thresholds = configuration.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("thresholds object is required")
    else:
        _validate_thresholds(thresholds, errors)
    actions = configuration.get("actions")
    if not isinstance(actions, dict):
        errors.append("actions object is required")
    else:
        _validate_actions(actions, errors)
    return errors


def _validate_thresholds(thresholds: dict[str, Any], errors: list[str]) -> None:
    if not thresholds.get("threshold_version"):
        errors.append("thresholds.threshold_version is required")
    domain_min = thresholds.get("domain_min")
    domain_max = thresholds.get("domain_max")
    if not isinstance(domain_min, int | float) or not isinstance(domain_max, int | float) or domain_min >= domain_max:
        errors.append("thresholds domain must have numeric domain_min < domain_max")
        return
    bands = thresholds.get("bands")
    if not isinstance(bands, list) or not bands:
        errors.append("thresholds.bands must be a non-empty list")
        return
    cursor = float(domain_min)
    for band in bands:
        if not isinstance(band, dict):
            errors.append("each threshold band must be an object")
            return
        if band.get("level") not in {"green", "yellow", "orange", "red"}:
            errors.append("threshold band level must be green, yellow, orange or red")
        minimum = band.get("minimum")
        maximum = band.get("maximum")
        if not isinstance(minimum, int | float) or not isinstance(maximum, int | float) or minimum >= maximum:
            errors.append("threshold band bounds must be numeric and increasing")
            continue
        if float(minimum) != cursor:
            errors.append("threshold bands must cover the domain without gaps or overlaps")
        cursor = float(maximum)
    if cursor != float(domain_max):
        errors.append("threshold bands must end at domain_max")


def _validate_actions(actions: dict[str, Any], errors: list[str]) -> None:
    if not actions.get("recommendation_version"):
        errors.append("actions.recommendation_version is required")
    templates = actions.get("templates")
    if not isinstance(templates, dict):
        errors.append("actions.templates object is required")
        return
    for level in ("green", "watch", "warning", "emergency", "unknown"):
        template = templates.get(level)
        if not isinstance(template, dict):
            errors.append(f"actions.templates.{level} is required")
            continue
        for field in ("action", "suggested_actor", "urgency"):
            if not isinstance(template.get(field), str) or not template[field].strip():
                errors.append(f"actions.templates.{level}.{field} is required")


def _version(row: sqlite3.Row) -> ConfigurationVersion:
    return ConfigurationVersion(
        version_id=row["version_id"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        status=row["status"],
        content_hash=row["content_hash"],
        configuration=json.loads(row["configuration_json"]),
        validation_errors=tuple(json.loads(row["validation_errors_json"])),
    )


def _content_hash(configuration: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


__all__ = [
    "AdminConfigurationRepository",
    "AdminValidationError",
    "ConfigurationVersion",
    "SCHEMA_VERSION",
    "admin_repository_from_env",
    "default_admin_configuration",
    "validate_admin_configuration",
]

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "mwangaza.exports.v1"
SENSITIVE_MARKERS = ("secret", "token", "private_key", "credential", "password")


@dataclass(frozen=True)
class VisibleExport:
    schema_version: str
    region_id: str
    region_label: str
    period: str
    rows: tuple[dict[str, Any], ...]
    source_metadata: dict[str, Any]
    include_geometry: bool = False


def build_visible_export(
    data: Any,
    *,
    region_id: str | None = None,
    max_rows: int = 500,
    include_geometry: bool = False,
) -> VisibleExport:
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")
    selected = (region_id or getattr(data, "selected_region_id", "")).lower()
    profile = _profile_for_region(data, selected)
    map_region = _map_region_for(data, selected)
    period = _period_label(data, map_region)
    rows = []
    for metric in tuple(getattr(profile, "metrics", ()) or getattr(data, "metrics", ())):
        row = {
            "row_type": "metric",
            "region_id": selected,
            "region_label": getattr(profile, "label", selected.upper()),
            "period": period,
            "name": metric.label,
            "value": _export_value(metric.value),
            "unit": metric.unit,
            "quality": metric.severity,
            "source": _sanitize(metric.detail),
        }
        if include_geometry and map_region is not None:
            row["ui_geometry"] = getattr(map_region, "ui_geometry", None)
        rows.append(row)
    for alert in getattr(profile, "alerts", ()):
        rows.append(
            {
                "row_type": "alert",
                "region_id": selected,
                "region_label": getattr(profile, "label", selected.upper()),
                "period": getattr(alert, "period", period),
                "name": getattr(alert, "title", ""),
                "value": getattr(alert, "score", None),
                "unit": "score",
                "quality": getattr(alert, "quality_flag", ""),
                "source": _sanitize("; ".join(f"{k}: {v}" for k, v in getattr(alert, "evidence", ()))),
            }
        )
    return VisibleExport(
        schema_version=SCHEMA_VERSION,
        region_id=selected,
        region_label=str(getattr(profile, "label", selected.upper())),
        period=period,
        rows=tuple(rows[:max_rows]),
        source_metadata={
            "data_source": _sanitize(getattr(getattr(data, "data_status", None), "source", "")),
            "last_updated": _sanitize(getattr(getattr(data, "data_status", None), "last_updated", "")),
            "row_limit": max_rows,
            "period_limited": True,
        },
        include_geometry=include_geometry,
    )


def export_visible_json(export: VisibleExport) -> str:
    payload = {
        "schema_version": export.schema_version,
        "region_id": export.region_id,
        "region_label": export.region_label,
        "period": export.period,
        "source_metadata": export.source_metadata,
        "include_geometry": export.include_geometry,
        "rows": [_sanitize_mapping(row, include_geometry=export.include_geometry) for row in export.rows],
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def export_visible_csv(export: VisibleExport) -> str:
    output = io.StringIO()
    fieldnames = ("row_type", "region_id", "region_label", "period", "name", "value", "unit", "quality", "source")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in export.rows:
        sanitized = _sanitize_mapping(row, include_geometry=False)
        writer.writerow({field: "" if sanitized.get(field) is None else sanitized.get(field, "") for field in fieldnames})
    return output.getvalue()


def safe_export_filename(export: VisibleExport, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext not in {"csv", "json"}:
        raise ValueError("unsupported export extension")
    return f"mwangaza-visible-export-{_slug(export.region_label)}-{_slug(export.period)}.{ext}"


def _profile_for_region(data: Any, region_id: str) -> Any:
    for profile in getattr(data, "region_profiles", ()):
        if getattr(profile, "region_id", "") == region_id:
            return profile
    return getattr(data, "region_profiles", (data,))[0] if getattr(data, "region_profiles", ()) else data


def _map_region_for(data: Any, region_id: str) -> Any:
    for region in getattr(getattr(data, "risk_map", None), "regions", ()):
        if getattr(region, "region_id", "") == region_id:
            return region
    return None


def _period_label(data: Any, map_region: Any) -> str:
    start = str(getattr(map_region, "period_start", "") or "")
    end = str(getattr(map_region, "period_end", "") or "")
    if start and end:
        return f"{start[:10]} to {end[:10]}"
    if getattr(data, "temporal_periods", ()):
        return str(data.temporal_periods[0].label)
    return str(getattr(getattr(data, "data_status", None), "last_updated", "") or "unknown-period")


def _export_value(value: Any) -> Any:
    if value in {None, "No data", ""}:
        return None
    if isinstance(value, int | float):
        return value
    text = str(value).replace(",", "")
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return float(text)
    return value


def _sanitize_mapping(row: dict[str, Any], *, include_geometry: bool) -> dict[str, Any]:
    sanitized = {}
    for key, value in row.items():
        if _sensitive(str(key)):
            continue
        if key == "ui_geometry" and not include_geometry:
            continue
        sanitized[key] = _sanitize(value)
    return sanitized


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if not _sensitive(str(key))}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        if _sensitive(value) or "\\" in value or re.search(r"[A-Za-z]:/", value.replace("\\", "/")):
            return "[redacted]"
        return value
    return value


def _sensitive(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SENSITIVE_MARKERS)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-") or "export"


__all__ = [
    "SCHEMA_VERSION",
    "VisibleExport",
    "build_visible_export",
    "export_visible_csv",
    "export_visible_json",
    "safe_export_filename",
]

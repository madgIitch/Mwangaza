from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from mwangaza import PROJECT_NAME, TAGLINE
from mwangaza.actions import recommend_actions
from mwangaza.config import ConfigurationError, load_settings
from mwangaza.contracts import RiskSnapshot
from mwangaza.maps import RegionalRiskMap, build_regional_risk_map, demo_regional_risk_map
from mwangaza.services.live_gee_dashboard import load_live_gee_dashboard_payloads

DataMode = Literal["live", "cache", "demo"]
Freshness = Literal["current", "stale", "error", "loading", "empty"]
Severity = Literal["normal", "watch", "warning", "critical", "unknown"]


@dataclass(frozen=True)
class NavigationItem:
    key: str
    label: str
    active: bool = False


@dataclass(frozen=True)
class DataStatus:
    mode: DataMode
    freshness: Freshness
    source: str
    last_updated: str
    message: str


@dataclass(frozen=True)
class RegionMetric:
    label: str
    value: str
    unit: str
    severity: Severity
    detail: str


@dataclass(frozen=True)
class AlertSummary:
    region: str
    severity: Severity
    title: str
    period: str
    action: str


@dataclass(frozen=True)
class DashboardShellData:
    project: str
    tagline: str
    selected_region: str
    data_status: DataStatus
    risk_map: RegionalRiskMap
    navigation: tuple[NavigationItem, ...]
    metrics: tuple[RegionMetric, ...]
    alerts: tuple[AlertSummary, ...]
    recommendations: tuple[str, ...]


def load_dashboard_shell_data(
    mode: DataMode | None = None,
    *,
    cache_dir: Path | None = None,
    data_dir: Path | None = None,
    alert_db_path: Path | None = None,
) -> DashboardShellData:
    """Load dashboard data from live GEE, then cache, then demo fallback."""

    if mode is not None:
        return _demo_dashboard_shell_data(mode)

    resolved_cache_dir, resolved_data_dir = _resolve_local_paths(cache_dir, data_dir)
    if cache_dir is None and data_dir is None and alert_db_path is None:
        live = _load_live_dashboard_data()
        if live is not None:
            _debug_dashboard("loader selected mode=live source=Google Earth Engine live query")
            return live

    materialized = _load_materialized_dashboard_data(
        resolved_cache_dir,
        alert_db_path or resolved_data_dir / "alerts.sqlite",
    )
    if materialized is not None:
        _debug_dashboard("loader selected mode=cache source=materialized local payloads")
        return materialized
    _debug_dashboard("loader selected mode=demo source=deterministic fallback")
    return _demo_dashboard_shell_data("demo")


def fallback_dashboard_shell_data() -> DashboardShellData:
    data = _demo_dashboard_shell_data("demo")
    return DashboardShellData(
        project=data.project,
        tagline=data.tagline,
        selected_region=data.selected_region,
        data_status=DataStatus(
            mode="demo",
            freshness="error",
            source="Safe fallback",
            last_updated=data.data_status.last_updated,
            message="Dashboard data could not be loaded",
        ),
        risk_map=data.risk_map,
        navigation=data.navigation,
        metrics=data.metrics,
        alerts=(),
        recommendations=("Retry after checking configuration and data refresh status.",),
    )


def _load_materialized_dashboard_data(cache_dir: Path, alert_db_path: Path) -> DashboardShellData | None:
    cached_payloads = _read_cached_payloads(cache_dir)
    return _dashboard_data_from_payloads(
        cached_payloads,
        alert_db_path,
        mode="cache",
        source_observed="Materialized observed data",
        source_simulated="Materialized cache",
        message_observed="Using cached observed data",
        message_simulated="Using cached demo data",
    )


def _load_live_dashboard_data() -> DashboardShellData | None:
    try:
        _debug_dashboard("trying live GEE dashboard payloads")
        payloads = tuple(load_live_gee_dashboard_payloads())
    except Exception as exc:
        _debug_dashboard(
            "live GEE unavailable; falling back to cache/demo "
            f"reason={type(exc).__name__}: {_sanitize_debug_message(str(exc))}"
        )
        return None
    _debug_dashboard(f"live GEE returned payload_count={len(payloads)}")
    return _dashboard_data_from_payloads(
        payloads,
        Path(),
        mode="live",
        source_observed="Google Earth Engine live query",
        source_simulated="Google Earth Engine live query",
        message_observed="Using live Google Earth Engine data",
        message_simulated="Using live Google Earth Engine data",
    )


def _dashboard_data_from_payloads(
    cached_payloads: tuple[dict[str, Any], ...],
    alert_db_path: Path,
    *,
    mode: DataMode,
    source_observed: str,
    source_simulated: str,
    message_observed: str,
    message_simulated: str,
) -> DashboardShellData | None:
    risk = _latest_risk_snapshot(cached_payloads)
    risks = _risk_snapshots(cached_payloads)
    snapshot = _latest_indicator_snapshot(cached_payloads)
    signals = _signals_for_view(cached_payloads, snapshot)
    if risk is None and snapshot is None and not signals:
        return None

    region_id = _first_text(
        risk.get("region_id") if risk else None,
        snapshot.get("region_id") if snapshot else None,
        *(signal.get("region_id") for signal in signals),
    )
    period_end = _first_text(
        risk.get("period_end") if risk else None,
        snapshot.get("newest_updated_at") if snapshot else None,
        *(signal.get("period_end") for signal in signals),
    )
    is_simulated = _all_simulated([payload for payload in (risk, snapshot, *signals) if payload])
    source = source_simulated if is_simulated else source_observed
    message = message_simulated if is_simulated else message_observed
    alerts = _read_active_alerts(alert_db_path) or _alerts_from_risk(risk)
    recommendations = _recommendations_from_alerts(alerts) or _recommendations_from_risk(risk)

    return DashboardShellData(
        project=PROJECT_NAME,
        tagline=TAGLINE,
        selected_region=_region_label(region_id),
        data_status=DataStatus(
            mode=mode,
            freshness="current",
            source=source,
            last_updated=_compact_time(period_end),
            message=message,
        ),
        risk_map=build_regional_risk_map(
            risks,
            selected_region_id=region_id or "som",
            source_mode=mode,
        ),
        navigation=_navigation(),
        metrics=_metrics_from_materialized(risk, signals),
        alerts=alerts,
        recommendations=recommendations or ("No action recommendations are available yet.",),
    )


def _read_cached_payloads(cache_dir: Path) -> tuple[dict[str, Any], ...]:
    if not cache_dir.is_dir():
        return ()
    payloads: list[dict[str, Any]] = []
    for path in sorted(cache_dir.rglob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        for payload in _extract_payloads(raw):
            payloads.append(payload)
    return tuple(payloads)


def _extract_payloads(raw: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, dict):
        return ()
    payload = raw.get("payload", raw)
    if isinstance(payload, dict):
        if isinstance(payload.get("signals"), list):
            signals = tuple(item for item in payload["signals"] if isinstance(item, dict))
            return (payload, *signals)
        return (payload,)
    if isinstance(payload, list):
        return tuple(item for item in payload if isinstance(item, dict))
    return ()


def _latest_risk_snapshot(payloads: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    risks = [payload for payload in payloads if payload.get("payload_type") == "risk_snapshot"]
    return max(risks, key=_payload_sort_time, default=None)


def _risk_snapshots(payloads: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(payload for payload in payloads if payload.get("payload_type") == "risk_snapshot")


def _latest_indicator_snapshot(payloads: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    snapshots = [
        payload
        for payload in payloads
        if isinstance(payload.get("snapshot_id"), str) and isinstance(payload.get("signals"), list)
    ]
    return max(snapshots, key=_payload_sort_time, default=None)


def _signals_for_view(
    payloads: tuple[dict[str, Any], ...],
    snapshot: dict[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    if snapshot is not None and isinstance(snapshot.get("signals"), list):
        return tuple(item for item in snapshot["signals"] if isinstance(item, dict))
    allowed = {"indicator_observation", "anomaly"}
    signals = [payload for payload in payloads if payload.get("payload_type") in allowed]
    if not signals:
        return ()
    latest_region = _first_text(max(signals, key=_payload_sort_time).get("region_id"))
    latest_period = _first_text(max(signals, key=_payload_sort_time).get("period_end"))
    filtered = [
        payload
        for payload in signals
        if payload.get("region_id") == latest_region and payload.get("period_end") == latest_period
    ]
    return tuple(sorted(filtered, key=lambda item: str(item.get("indicator", ""))))


def _read_active_alerts(alert_db_path: Path) -> tuple[AlertSummary, ...]:
    if not alert_db_path.is_file():
        return ()
    try:
        conn = sqlite3.connect(alert_db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT region_id, severity, period_start, period_end, score, quality_flag
            FROM alerts
            WHERE status='active'
            ORDER BY
              CASE severity
                WHEN 'emergency' THEN 0
                WHEN 'critical' THEN 1
                WHEN 'warning' THEN 2
                WHEN 'watch' THEN 3
                ELSE 4
              END,
              period_end DESC
            LIMIT 5
            """
        ).fetchall()
    except sqlite3.Error:
        return ()
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass
    return tuple(
        AlertSummary(
            region=_region_label(str(row["region_id"])),
            severity=_severity(str(row["severity"])),
            title=_alert_title(str(row["severity"]), row["score"]),
            period=_period_label(str(row["period_start"]), str(row["period_end"])),
            action="View details",
        )
        for row in rows
    )


def _alerts_from_risk(risk: dict[str, Any] | None) -> tuple[AlertSummary, ...]:
    if risk is None:
        return ()
    level = _risk_level(risk)
    if level in {"low", "unknown"}:
        return ()
    return (
        AlertSummary(
            region=_region_label(_first_text(risk.get("region_id"))),
            severity=_severity(level),
            title=_alert_title(level, risk.get("composite_score")),
            period=_period_label(
                _first_text(risk.get("period_start")),
                _first_text(risk.get("period_end")),
            ),
            action="View details",
        ),
    )


def _recommendations_from_risk(risk: dict[str, Any] | None) -> tuple[str, ...]:
    if risk is None:
        return ()
    try:
        snapshot = RiskSnapshot.from_dict(risk)
        return tuple(item.action for item in recommend_actions(snapshot))
    except Exception:
        return ()


def _recommendations_from_alerts(alerts: tuple[AlertSummary, ...]) -> tuple[str, ...]:
    if not alerts:
        return ()
    top = alerts[0]
    if top.severity == "critical":
        return ("Activate urgent coordination review.",)
    if top.severity == "warning":
        return ("Preposition supplies and brief partners.",)
    if top.severity == "watch":
        return ("Prepare early action checklist.",)
    return ()


def _metrics_from_materialized(
    risk: dict[str, Any] | None,
    signals: tuple[dict[str, Any], ...],
) -> tuple[RegionMetric, ...]:
    by_indicator = {str(signal.get("indicator")): signal for signal in signals}
    return (
        _metric_from_signal(by_indicator.get("ndvi"), "NDVI anomaly", "index"),
        _metric_from_signal(by_indicator.get("rainfall_mm"), "Rainfall anomaly", "mm"),
        _metric_from_signal(by_indicator.get("lst_c"), "LST anomaly", "C"),
        _risk_metric(risk),
        _quality_metric(risk, signals),
        _metric_from_signal(by_indicator.get("exposure"), "Exposed population", "est."),
    )


def _metric_from_signal(signal: dict[str, Any] | None, label: str, default_unit: str) -> RegionMetric:
    if signal is None or signal.get("value") is None:
        return RegionMetric(label, "No data", "", "unknown", "No materialized value")
    value = signal.get("value")
    unit = str(signal.get("unit") or default_unit)
    return RegionMetric(
        label=label,
        value=_format_number(value),
        unit=unit,
        severity=_quality_severity(str(signal.get("quality_flag", "invalid"))),
        detail=str(signal.get("source") or "materialized source"),
    )


def _risk_metric(risk: dict[str, Any] | None) -> RegionMetric:
    if risk is None or risk.get("composite_score") is None:
        return RegionMetric("Composite score", "No data", "", "unknown", "No materialized risk")
    level = _risk_level(risk)
    return RegionMetric(
        "Composite score",
        _format_number(risk.get("composite_score")),
        "/100",
        _severity(level),
        f"Risk level: {level}",
    )


def _quality_metric(risk: dict[str, Any] | None, signals: tuple[dict[str, Any], ...]) -> RegionMetric:
    flags = [str(signal.get("quality_flag", "invalid")) for signal in signals]
    if risk is not None:
        flags.append(str(risk.get("quality_flag", "invalid")))
    if not flags:
        return RegionMetric("Data quality", "No data", "", "unknown", "No materialized quality")
    if "invalid" in flags or "no_data" in flags:
        return RegionMetric("Data quality", "Review", "", "critical", "Missing or invalid indicators")
    if "degraded" in flags or "insufficient_history" in flags:
        return RegionMetric("Data quality", "Degraded", "", "warning", "Use with caution")
    return RegionMetric("Data quality", "Good", "", "normal", "Materialized indicators available")


def _demo_dashboard_shell_data(mode: DataMode = "demo") -> DashboardShellData:
    status_by_mode = {
        "live": DataStatus(
            mode="live",
            freshness="current",
            source="Live pipeline",
            last_updated="2026-07-15 16:00 UTC",
            message="Data is current",
        ),
        "cache": DataStatus(
            mode="cache",
            freshness="stale",
            source="Versioned cache",
            last_updated="2026-07-14 06:00 UTC",
            message="Using cached data",
        ),
        "demo": DataStatus(
            mode="demo",
            freshness="current",
            source="Demo fixture",
            last_updated="2026-07-15 16:00 UTC",
            message="Data is current",
        ),
    }
    return DashboardShellData(
        project=PROJECT_NAME,
        tagline=TAGLINE,
        selected_region="Somalia",
        data_status=status_by_mode[mode],
        risk_map=demo_regional_risk_map(selected_region_id="som"),
        navigation=_navigation(),
        metrics=(
            RegionMetric("NDVI anomaly", "-0.18", "z", "warning", "Vegetation stress"),
            RegionMetric("Rainfall anomaly", "-42", "%", "critical", "Below seasonal baseline"),
            RegionMetric("LST anomaly", "+2.4", "C", "warning", "Surface heat elevated"),
            RegionMetric("Composite score", "78", "/100", "critical", "High drought risk"),
            RegionMetric("Data quality", "Good", "", "normal", "Most indicators available"),
            RegionMetric("Exposed population", "1.2M", "est.", "watch", "Exposure estimate"),
        ),
        alerts=(
            AlertSummary(
                "Somalia",
                "critical",
                "Drought risk escalation",
                "Jul 2026",
                "View details",
            ),
            AlertSummary(
                "Northern Kenya",
                "warning",
                "Rainfall deficit watch",
                "Jul 2026",
                "View details",
            ),
            AlertSummary(
                "Ethiopia",
                "watch",
                "Vegetation stress emerging",
                "Jul 2026",
                "View details",
            ),
        ),
        recommendations=(
            "Prioritize water trucking readiness in high-risk districts.",
            "Pre-position livestock feed in pastoral corridors.",
            "Coordinate district verification before publishing alerts.",
        ),
    )


def _navigation() -> tuple[NavigationItem, ...]:
    return (
        NavigationItem("overview", "Overview", True),
        NavigationItem("region", "Region"),
        NavigationItem("alerts", "Alerts"),
        NavigationItem("reports", "Reports"),
        NavigationItem("about", "About"),
    )


def _resolve_local_paths(cache_dir: Path | None, data_dir: Path | None) -> tuple[Path, Path]:
    if cache_dir is not None and data_dir is not None:
        return cache_dir, data_dir
    try:
        settings = load_settings()
    except ConfigurationError:
        settings = None
    return (
        cache_dir or (settings.cache_dir if settings is not None else Path("./.cache/mwangaza")),
        data_dir or (settings.data_dir if settings is not None else Path("./data")),
    )


def _payload_sort_time(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata", {})
    updated_at = metadata.get("updated_at") if isinstance(metadata, dict) else None
    return str(
        updated_at
        or payload.get("newest_updated_at")
        or payload.get("period_end")
        or payload.get("created_at")
        or ""
    )


def _all_simulated(payloads: list[dict[str, Any]]) -> bool:
    flags = [payload.get("is_simulated") for payload in payloads if "is_simulated" in payload]
    return bool(flags) and all(flag is True for flag in flags)


def _risk_level(risk: dict[str, Any]) -> str:
    metadata = risk.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("risk_level_override") == "unknown":
        return "unknown"
    return str(risk.get("risk_level") or "unknown")


def _severity(value: str) -> Severity:
    normalized = value.lower()
    if normalized in {"emergency", "critical"}:
        return "critical"
    if normalized == "warning":
        return "warning"
    if normalized == "watch":
        return "watch"
    if normalized in {"low", "ok", "normal", "green"}:
        return "normal"
    return "unknown"


def _quality_severity(quality_flag: str) -> Severity:
    if quality_flag == "ok":
        return "normal"
    if quality_flag == "degraded":
        return "watch"
    if quality_flag == "insufficient_history":
        return "warning"
    return "unknown"


def _alert_title(level: str, score: object) -> str:
    suffix = f" ({_format_number(score)}/100)" if isinstance(score, int | float) else ""
    if level in {"emergency", "critical"}:
        return f"Drought risk escalation{suffix}"
    if level == "warning":
        return f"Drought warning{suffix}"
    if level == "watch":
        return f"Drought watch{suffix}"
    return f"Drought status{suffix}"


def _period_label(period_start: str, period_end: str) -> str:
    if period_start and period_end:
        return f"{period_start[:10]} to {period_end[:10]}"
    return period_end[:10] if period_end else "Unknown period"


def _compact_time(value: str) -> str:
    return value.replace("T", " ").replace("Z", " UTC") if value else "Unknown update"


def _region_label(region_id: str) -> str:
    if not region_id:
        return "Unknown region"
    return region_id.upper()


def _first_text(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _format_number(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _debug_dashboard(message: str) -> None:
    if os.environ.get("MWANGAZA_DASHBOARD_DEBUG") == "1":
        print(f"[mwangaza.dashboard] {message}")


def _sanitize_debug_message(message: str) -> str:
    blocked = ("private_key", "service_account", "token", "secret", "password")
    if any(part in message.lower() for part in blocked):
        return "[redacted]"
    return message[:240]

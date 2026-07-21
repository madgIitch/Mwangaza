from __future__ import annotations

import json
import os
import time
from http import HTTPStatus
from urllib.parse import parse_qs
from typing import Any

from mwangaza._foundation import foundation_status
from mwangaza.admin import (
    AdminValidationError,
    admin_repository_from_env,
)
from mwangaza.config import public_config_status
from mwangaza.exports import build_visible_export
from mwangaza.gee.auth import check_gee_auth
from mwangaza.observability import METRICS, bind_run_id, current_run_id, emit, readiness_status, reset_run_id, resolve_run_id
from mwangaza.security import RATE_LIMITER, SECURITY_HEADERS, SecurityRequestError, validate_body_contract, validate_request_target
from mwangaza.regions import list_regions
from mwangaza.services.dashboard_shell import load_dashboard_shell_data

API_SCHEMA_VERSION = "mwangaza.api.v1"
DEMO_REFERENCE_DATE = "2026-07-15"
DEMO_SNAPSHOT_ID = "mwangaza-offline-demo-v1"
MAX_LIMIT = 100
LIVE_DASHBOARD_CACHE_SECONDS = 120
_DASHBOARD_CACHE: tuple[float, Any] | None = None


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return
    request_started = time.monotonic()
    run_id = resolve_run_id(_header(scope.get("headers", []), "x-run-id"))
    token = bind_run_id(run_id)
    try:
        try:
            await _handle_http(scope, receive, send)
        except SecurityRequestError as exc:
            METRICS.record_error()
            await _send_json(send, _error(exc.code, str(exc)), exc.status)
            _log("security request rejected", level="WARNING", code=exc.code, status=exc.status)
    finally:
        METRICS.record_request(_elapsed_ms(request_started))
        reset_run_id(token)


async def _handle_http(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    validate_request_target(path)
    client = scope.get("client") or ("unknown", 0)
    RATE_LIMITER.check(str(client[0]))
    request_started = time.monotonic()
    query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
    _log("request start", path=path, query=query_string or "-")
    if path == "/health":
        payload = foundation_status().as_dict() | public_config_status()
        if _is_demo_mode():
            payload["gee"] = {"status": "not_initialized", "message": "Disabled in explicit demo mode"}
            payload.update(_demo_metadata())
        else:
            payload["gee"] = check_gee_auth().to_public_dict()
        payload["observability"] = {"run_id": current_run_id(), "status": "ok"}
        gee_payload = payload["gee"]
        gee_status = gee_payload.get("status", "unknown") if isinstance(gee_payload, dict) else "unknown"
        _log("health checked", gee_status=gee_status)
        await _send_json(send, payload, HTTPStatus.OK)
        _log("request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started))
        return
    if path == "/ready":
        readiness = readiness_status()
        status = HTTPStatus.OK if readiness.ready else HTTPStatus.SERVICE_UNAVAILABLE
        await _send_json(send, readiness.to_public_dict() | {"run_id": current_run_id()}, status)
        _log("readiness checked", status=status, checks=readiness.checks)
        return
    if path == "/openapi.json":
        await _send_json(send, _openapi(), HTTPStatus.OK)
        _log("request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started))
        return
    if path.startswith("/api/v1/"):
        try:
            body = await _read_body(receive)
            validate_body_contract(path, body, _header(scope.get("headers", []), "content-type"))
            payload, status, cache_seconds = _route_v1(path, scope.get("query_string", b""), scope.get("headers", []), body)
            if _is_demo_mode():
                payload.update(_demo_metadata())
            await _send_json(send, payload, status, cache_seconds=cache_seconds)
            _log(
                "request end",
                path=path,
                status=status,
                elapsed_ms=_elapsed_ms(request_started),
                summary=_payload_summary(path, payload),
            )
        except SecurityRequestError:
            raise
        except AdminValidationError as exc:
            METRICS.record_error()
            await _send_json(send, {"error": {"code": "admin_validation_failed", "message": "Configuration is invalid", "details": exc.errors}}, HTTPStatus.BAD_REQUEST)
            _log("request error", path=path, status=HTTPStatus.BAD_REQUEST, error="admin_validation_failed", elapsed_ms=_elapsed_ms(request_started))
        except ValueError as exc:
            METRICS.record_error()
            await _send_json(send, _error("invalid_request", str(exc)), HTTPStatus.BAD_REQUEST)
            _log("request error", path=path, status=HTTPStatus.BAD_REQUEST, error=str(exc), elapsed_ms=_elapsed_ms(request_started))
        except Exception:
            METRICS.record_error()
            await _send_json(send, _error("internal_error", "Request could not be served"), HTTPStatus.INTERNAL_SERVER_ERROR)
            _log("request error", path=path, status=HTTPStatus.INTERNAL_SERVER_ERROR, error="internal_error", elapsed_ms=_elapsed_ms(request_started))
        return
    else:
        await _send_json(
            send,
            _error("not_found", "Use /health or /api/v1 endpoints."),
            HTTPStatus.NOT_FOUND,
        )
        _log("request end", path=path, status=HTTPStatus.NOT_FOUND, elapsed_ms=_elapsed_ms(request_started))
        return


def _route_v1(
    path: str,
    query_string: bytes,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
) -> tuple[dict[str, Any], HTTPStatus, int | None]:
    query = parse_qs(query_string.decode("utf-8", errors="ignore"))
    if path == "/api/v1/regions":
        limit, offset = _pagination(query)
        regions = [
            {
                "id": region.id,
                "name": region.name,
                "iso3": region.iso3,
                "level": region.level,
                "is_pilot": region.is_pilot,
                "coverage_type": region.coverage_type,
            }
            for region in list_regions(include_pilots=True)
        ]
        METRICS.observe_workload(regions_processed=len(regions))
        return _listed(regions, limit, offset), HTTPStatus.OK, 60
    if path == "/api/v1/snapshots/latest":
        data = _load_api_dashboard_data()
        export = build_visible_export(data, max_rows=MAX_LIMIT)
        _log(
            "snapshot export",
            data_mode=data.data_status.mode,
            region_id=export.region_id,
            period=export.period,
            row_count=len(export.rows),
            source=export.source_metadata.get("data_source", export.source_metadata.get("source", "unknown")),
        )
        return {
            "schema_version": API_SCHEMA_VERSION,
            "data_mode": data.data_status.mode,
            "snapshot": {
                "region_id": export.region_id,
                "region_label": export.region_label,
                "period": export.period,
                "rows": export.rows,
                "regional_risk": _regional_risk(data),
                "region_profiles": _region_profiles(data),
                "periods": _dashboard_periods(data),
                "source_metadata": export.source_metadata,
            },
        }, HTTPStatus.OK, 60
    if path == "/api/v1/alerts":
        limit, offset = _pagination(query)
        data = _load_api_dashboard_data()
        alerts = [
            {
                "region_id": alert.region_id,
                "region": alert.region,
                "severity": alert.severity,
                "status": alert.status,
                "title": alert.title,
                "period": alert.period,
                "quality_flag": alert.quality_flag,
                "recommended_action": alert.recommended_action or alert.action,
            }
            for alert in data.alerts
        ]
        _log("alerts export", data_mode=data.data_status.mode, total=len(alerts), limit=limit, offset=offset)
        METRICS.observe_workload(active_alerts=len(alerts))
        return _listed(alerts, limit, offset), HTTPStatus.OK, 60
    if path == "/api/v1/forecasts":
        limit, offset = _pagination(query)
        return _listed([], limit, offset) | {"available": False, "message": "Forecasts are not available yet"}, HTTPStatus.OK, 60
    if path == "/api/v1/observability":
        readiness = readiness_status()
        return {
            "schema_version": API_SCHEMA_VERSION,
            "run_id": current_run_id(),
            "status": "operational" if readiness.ready else "degraded",
            "readiness": readiness.to_public_dict(),
            "metrics": METRICS.snapshot(),
        }, HTTPStatus.OK, None
    if path == "/api/v1/admin/config":
        repo = admin_repository_from_env()
        try:
            if body:
                payload = _json_body(body)
                version = repo.create_version(payload.get("configuration", {}), actor="public-admin", activate=bool(payload.get("activate", False)))
                return _admin_payload(repo, version=version), HTTPStatus.CREATED, None
            return _admin_payload(repo), HTTPStatus.OK, None
        finally:
            repo.close()
    if path == "/api/v1/admin/config/activate":
        payload = _json_body(body)
        repo = admin_repository_from_env()
        try:
            version = repo.activate_version(str(payload.get("version_id", "")), actor="public-admin")
            return _admin_payload(repo, version=version), HTTPStatus.OK, None
        finally:
            repo.close()
    if path == "/api/v1/admin/status":
        return {
            "schema_version": API_SCHEMA_VERSION,
            "admin": {
                "access": "public",
                "auth": "none",
                "institutional_auth": False,
            },
        }, HTTPStatus.OK, None
    raise ValueError("unknown v1 endpoint")


def _admin_payload(repo: Any, *, version: Any | None = None) -> dict[str, Any]:
    active = repo.get_active()
    versions = repo.list_versions()
    return {
        "schema_version": API_SCHEMA_VERSION,
        "admin_schema_version": "mwangaza.admin.v1",
        "active_version": active.to_public_dict() if active else None,
        "saved_version": version.to_public_dict() if version else None,
        "versions": [item.to_public_dict() for item in versions],
        "security": {
            "access": "public",
            "auth": "none",
            "institutional_auth": False,
        },
        "recalculation": {
            "triggered": False,
            "message": "Configuration changes do not refresh indicators, cache, forecasts or alerts.",
        },
    }


def _json_body(body: bytes) -> dict[str, Any]:
    if not body:
        raise ValueError("request body is required")
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("request body must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(message.get("body", b""))
        if sum(len(chunk) for chunk in chunks) > 64 * 1024:
            raise SecurityRequestError("payload_too_large", "Request body exceeds 64 KiB", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _header(headers: list[tuple[bytes, bytes]], name: str) -> str:
    key = name.lower().encode("ascii")
    for raw_key, raw_value in headers:
        if raw_key.lower() == key:
            return raw_value.decode("utf-8", errors="ignore")
    return ""


def _load_api_dashboard_data() -> Any:
    """Load dashboard data for API responses.

    Default remains deterministic demo data so public API tests and local dev do
    not trigger remote Earth Engine queries. Set MWANGAZA_API_DATA_MODE=live to
    use the normal dashboard loader, which attempts live GEE, then cache, then
    demo fallback.
    """

    configured = os.environ.get("MWANGAZA_MODE", "").strip().lower()
    default_mode = "live" if configured == "production" else "demo"
    mode = "demo" if configured == "demo" else os.environ.get("MWANGAZA_API_DATA_MODE", default_mode).strip().lower()
    _log("dashboard load requested", configured_mode=mode or "demo")
    if mode in {"live", "auto"}:
        return _cached_live_dashboard_data()
    if mode == "cache":
        return _cached_live_dashboard_data()
    data = load_dashboard_shell_data("demo")
    _log("dashboard load complete", selected_mode="demo", data_mode=data.data_status.mode)
    return data


def _is_demo_mode() -> bool:
    return os.environ.get("MWANGAZA_MODE", "").strip().lower() == "demo"


def _demo_metadata() -> dict[str, Any]:
    return {"data_mode": "demo", "is_demo": True, "reference_date": DEMO_REFERENCE_DATE, "snapshot_id": DEMO_SNAPSHOT_ID}


def _cached_live_dashboard_data() -> Any:
    global _DASHBOARD_CACHE
    now = time.monotonic()
    if _DASHBOARD_CACHE is not None:
        cached_at, data = _DASHBOARD_CACHE
        age_seconds = now - cached_at
        if age_seconds < LIVE_DASHBOARD_CACHE_SECONDS:
            METRICS.record_cache(True)
            _log("dashboard cache hit", age_s=round(age_seconds, 2), data_mode=data.data_status.mode)
            return data
        _log("dashboard cache expired", age_s=round(age_seconds, 2))
    METRICS.record_cache(False)
    started = time.monotonic()
    _log("dashboard live load start")
    data = load_dashboard_shell_data()
    if os.environ.get("MWANGAZA_MODE", "").strip().lower() == "production" and data.data_status.mode == "demo":
        raise RuntimeError("production data unavailable; implicit demo fallback is disabled")
    _DASHBOARD_CACHE = (time.monotonic(), data)
    _log("dashboard live load complete", elapsed_ms=_elapsed_ms(started), data_mode=data.data_status.mode, source=data.data_status.source)
    return data


def _pagination(query: dict[str, list[str]]) -> tuple[int, int]:
    limit = _int_param(query, "limit", 50)
    offset = _int_param(query, "offset", 0)
    if limit <= 0:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    return min(limit, MAX_LIMIT), offset


def _int_param(query: dict[str, list[str]], name: str, default: int) -> int:
    if name not in query:
        return default
    try:
        return int(query[name][0])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _listed(items: list[dict[str, Any]], limit: int, offset: int) -> dict[str, Any]:
    return {
        "schema_version": API_SCHEMA_VERSION,
        "items": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
        "total": len(items),
    }


def _error(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def _openapi() -> dict[str, Any]:
    examples = {
        "/api/v1/regions": {"limit": 10, "offset": 0},
        "/api/v1/snapshots/latest": {"schema_version": API_SCHEMA_VERSION},
        "/api/v1/alerts": {"limit": 10, "offset": 0},
        "/api/v1/forecasts": {"available": False},
        "/api/v1/admin/status": {"admin": {"configured": False}},
        "/api/v1/admin/config": {"active_version": None},
        "/api/v1/admin/config/activate": {"version_id": "cfg-example"},
        "/api/v1/observability": {"status": "operational"},
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Mwangaza Public API", "version": "v1"},
        "paths": {
            path: {"get": {"responses": {"200": {"description": "OK"}}, "x-example": example}}
            for path, example in examples.items()
        }
        | {
            "/health": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/ready": {"get": {"responses": {"200": {"description": "Ready"}, "503": {"description": "Not ready"}}}},
        },
    }


async def _send_json(
    send: Any,
    payload: dict[str, Any],
    status: HTTPStatus,
    *,
    cache_seconds: int | None = None,
) -> None:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    headers = [(b"content-type", b"application/json"), (b"x-run-id", current_run_id().encode("ascii"))]
    headers.extend((name.encode("ascii"), value.encode("ascii")) for name, value in SECURITY_HEADERS.items())
    if cache_seconds is not None:
        headers.append((b"cache-control", f"public, max-age={cache_seconds}".encode("ascii")))
    await send(
        {
            "type": "http.response.start",
            "status": int(status),
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": body})


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _payload_summary(path: str, payload: dict[str, Any]) -> str:
    if path == "/api/v1/snapshots/latest":
        snapshot = payload.get("snapshot", {})
        rows = snapshot.get("rows", []) if isinstance(snapshot, dict) else []
        regional = snapshot.get("regional_risk", []) if isinstance(snapshot, dict) else []
        return f"mode={payload.get('data_mode')} region={snapshot.get('region_id')} rows={len(rows)} regional={len(regional)}"
    if path == "/api/v1/alerts":
        return f"total={payload.get('total')} returned={len(payload.get('items', []))}"
    if path == "/api/v1/forecasts":
        return f"available={payload.get('available')} total={payload.get('total')}"
    if path == "/api/v1/regions":
        return f"total={payload.get('total')} returned={len(payload.get('items', []))}"
    return "ok"


def _log(event: str, **fields: Any) -> None:
    emit(event, component="api", **fields)


def _regional_risk(data: Any) -> list[dict[str, Any]]:
    regions = []
    for region in getattr(getattr(data, "risk_map", None), "regions", ()):
        regions.append(
            {
                "id": getattr(region, "region_id", ""),
                "name": getattr(region, "name", ""),
                "score": getattr(region, "score", None),
                "level": getattr(region, "risk_level", "unknown"),
                "color_level": getattr(region, "color_level", "unknown"),
                "quality": getattr(region, "quality_flag", "unknown"),
                "period_start": getattr(region, "period_start", ""),
                "period_end": getattr(region, "period_end", ""),
                "selected": bool(getattr(region, "selected", False)),
                "source_mode": getattr(region, "source_mode", ""),
                "ui_geometry": getattr(region, "ui_geometry", None),
            }
        )
    return regions


def _region_profiles(data: Any) -> list[dict[str, Any]]:
    return _serialize_region_profiles(getattr(data, "region_profiles", ()))


def _serialize_region_profiles(source: Any) -> list[dict[str, Any]]:
    profiles = []
    for profile in source:
        comparison = getattr(profile, "historical_comparison", None)
        profiles.append(
            {
                "id": profile.region_id,
                "name": profile.label,
                "status": profile.status,
                "metrics": [
                    {
                        "label": metric.label,
                        "value": metric.value,
                        "unit": metric.unit,
                        "severity": metric.severity,
                        "detail": metric.detail,
                    }
                    for metric in profile.metrics
                ],
                "pilot_units": [
                    {
                        "id": unit.pilot_id,
                        "name": unit.name,
                        "admin_level": unit.level,
                        "score": unit.score,
                        "level": unit.risk_level,
                        "quality": unit.quality_flag,
                        "rank": unit.rank,
                    }
                    for unit in profile.pilot_units
                ],
                "administrative_units": [
                    {
                        "region_id": unit.region_id,
                        "boundary_id": unit.boundary_id,
                        "boundary_iso": unit.boundary_iso,
                        "name": unit.name,
                        "parent_id": unit.parent_id,
                        "admin_level": unit.admin_level,
                        "score": unit.score,
                        "level": unit.risk_level,
                        "quality": unit.quality_flag,
                        "period_start": unit.period_start,
                        "period_end": unit.period_end,
                        "source_mode": unit.source_mode,
                        "geometry_source": unit.geometry_source,
                        "metrics": {
                            "ndvi": unit.ndvi,
                            "rainfall_mm": unit.rainfall_mm,
                            "lst_c": unit.lst_c,
                        },
                        "contributions": list(unit.contributions),
                        "rank": unit.rank,
                    }
                    for unit in profile.administrative_units
                ],
                "trends": [
                    {
                        "indicator": trend.indicator,
                        "label": trend.label,
                        "unit": trend.unit,
                        "source": trend.source,
                        "baseline_label": trend.baseline_label,
                        "points": [
                            {
                                "period": f"{point.period_start} to {point.period_end}",
                                "value": point.value,
                                "baseline": point.baseline_value,
                                "anomaly": point.anomaly_value,
                                "quality": point.quality_flag,
                                "is_gap": point.is_gap,
                            }
                            for point in trend.points
                        ],
                    }
                    for trend in profile.trends
                ],
                "historical_rows": [
                    {
                        "period": row.period_key,
                        "indicator": row.label,
                        "current": f"{row.current_value:g} {row.unit}".strip(),
                        "historical": f"{row.historical_value:g} {row.unit}".strip(),
                        "difference": f"{row.difference:+g} {row.unit}".strip(),
                        "version": row.data_version,
                    }
                    for row in (() if comparison is None else comparison.rows)
                ],
                "recommendations": list(profile.recommendations),
                "contributions": list(profile.contributions),
            }
        )
    return profiles


def _dashboard_periods(data: Any) -> list[dict[str, Any]]:
    return [
        {
            "key": period.period_key,
            "label": period.label,
            "regions": [
                {
                    "id": region.region_id,
                    "name": region.name,
                    "score": region.score,
                    "level": region.risk_level,
                    "color_level": region.color_level,
                    "quality": region.quality_flag,
                    "period_start": region.period_start,
                    "period_end": region.period_end,
                    "selected": region.selected,
                    "source_mode": region.source_mode,
                    "ui_geometry": region.ui_geometry,
                }
                for region in period.risk_map.regions
            ],
            "profiles": _serialize_region_profiles(period.region_profiles),
        }
        for period in getattr(data, "temporal_periods", ())
    ]

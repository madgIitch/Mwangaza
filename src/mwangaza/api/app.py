from __future__ import annotations

import json
import os
import time
from http import HTTPStatus
from urllib.parse import parse_qs
from typing import Any

from mwangaza._foundation import foundation_status
from mwangaza.config import public_config_status
from mwangaza.exports import build_visible_export
from mwangaza.gee.auth import check_gee_auth
from mwangaza.regions import list_regions
from mwangaza.services.dashboard_shell import load_dashboard_shell_data

API_SCHEMA_VERSION = "mwangaza.api.v1"
MAX_LIMIT = 100
LIVE_DASHBOARD_CACHE_SECONDS = 120
_DASHBOARD_CACHE: tuple[float, Any] | None = None


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    request_started = time.monotonic()
    query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
    _log("request start", path=path, query=query_string or "-")
    if path == "/health":
        payload = foundation_status().as_dict() | public_config_status()
        payload["gee"] = check_gee_auth().to_public_dict()
        await _send_json(send, payload, HTTPStatus.OK)
        _log("request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started))
        return
    if path == "/openapi.json":
        await _send_json(send, _openapi(), HTTPStatus.OK)
        _log("request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started))
        return
    if path.startswith("/api/v1/"):
        try:
            payload = _route_v1(path, scope.get("query_string", b""))
            await _send_json(send, payload, HTTPStatus.OK, cache_seconds=60)
            _log(
                "request end",
                path=path,
                status=HTTPStatus.OK,
                elapsed_ms=_elapsed_ms(request_started),
                summary=_payload_summary(path, payload),
            )
        except ValueError as exc:
            await _send_json(send, _error("invalid_request", str(exc)), HTTPStatus.BAD_REQUEST)
            _log("request error", path=path, status=HTTPStatus.BAD_REQUEST, error=str(exc), elapsed_ms=_elapsed_ms(request_started))
        except Exception:
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


def _route_v1(path: str, query_string: bytes) -> dict[str, Any]:
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
        return _listed(regions, limit, offset)
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
                "source_metadata": export.source_metadata,
            },
        }
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
        return _listed(alerts, limit, offset)
    if path == "/api/v1/forecasts":
        limit, offset = _pagination(query)
        return _listed([], limit, offset) | {"available": False, "message": "Forecasts are not available yet"}
    raise ValueError("unknown v1 endpoint")


def _load_api_dashboard_data() -> Any:
    """Load dashboard data for API responses.

    Default remains deterministic demo data so public API tests and local dev do
    not trigger remote Earth Engine queries. Set MWANGAZA_API_DATA_MODE=live to
    use the normal dashboard loader, which attempts live GEE, then cache, then
    demo fallback.
    """

    mode = os.environ.get("MWANGAZA_API_DATA_MODE", "demo").strip().lower()
    _log("dashboard load requested", configured_mode=mode or "demo")
    if mode in {"live", "auto"}:
        return _cached_live_dashboard_data()
    if mode == "cache":
        return _cached_live_dashboard_data()
    data = load_dashboard_shell_data("demo")
    _log("dashboard load complete", selected_mode="demo", data_mode=data.data_status.mode)
    return data


def _cached_live_dashboard_data() -> Any:
    global _DASHBOARD_CACHE
    now = time.monotonic()
    if _DASHBOARD_CACHE is not None:
        cached_at, data = _DASHBOARD_CACHE
        age_seconds = now - cached_at
        if age_seconds < LIVE_DASHBOARD_CACHE_SECONDS:
            _log("dashboard cache hit", age_s=round(age_seconds, 2), data_mode=data.data_status.mode)
            return data
        _log("dashboard cache expired", age_s=round(age_seconds, 2))
    started = time.monotonic()
    _log("dashboard live load start")
    data = load_dashboard_shell_data()
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
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Mwangaza Public API", "version": "v1"},
        "paths": {
            path: {"get": {"responses": {"200": {"description": "OK"}}, "x-example": example}}
            for path, example in examples.items()
        }
        | {"/health": {"get": {"responses": {"200": {"description": "OK"}}}}},
    }


async def _send_json(
    send: Any,
    payload: dict[str, Any],
    status: HTTPStatus,
    *,
    cache_seconds: int | None = None,
) -> None:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    headers = [(b"content-type", b"application/json")]
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
    serialized = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"[mwangaza.api] {event} {serialized}".rstrip(), flush=True)


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
            }
        )
    return regions

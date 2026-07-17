from __future__ import annotations

import json
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


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    if path == "/health":
        payload = foundation_status().as_dict() | public_config_status()
        payload["gee"] = check_gee_auth().to_public_dict()
        await _send_json(send, payload, HTTPStatus.OK)
        return
    if path == "/openapi.json":
        await _send_json(send, _openapi(), HTTPStatus.OK)
        return
    if path.startswith("/api/v1/"):
        try:
            payload = _route_v1(path, scope.get("query_string", b""))
            await _send_json(send, payload, HTTPStatus.OK, cache_seconds=60)
        except ValueError as exc:
            await _send_json(send, _error("invalid_request", str(exc)), HTTPStatus.BAD_REQUEST)
        except Exception:
            await _send_json(send, _error("internal_error", "Request could not be served"), HTTPStatus.INTERNAL_SERVER_ERROR)
        return
    else:
        await _send_json(
            send,
            _error("not_found", "Use /health or /api/v1 endpoints."),
            HTTPStatus.NOT_FOUND,
        )
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
        data = load_dashboard_shell_data("demo")
        export = build_visible_export(data, max_rows=MAX_LIMIT)
        return {
            "schema_version": API_SCHEMA_VERSION,
            "data_mode": data.data_status.mode,
            "snapshot": {
                "region_id": export.region_id,
                "region_label": export.region_label,
                "period": export.period,
                "rows": export.rows,
                "source_metadata": export.source_metadata,
            },
        }
    if path == "/api/v1/alerts":
        limit, offset = _pagination(query)
        data = load_dashboard_shell_data("demo")
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
        return _listed(alerts, limit, offset)
    if path == "/api/v1/forecasts":
        limit, offset = _pagination(query)
        return _listed([], limit, offset) | {"available": False, "message": "Forecasts are not available yet"}
    raise ValueError("unknown v1 endpoint")


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

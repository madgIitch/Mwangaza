from __future__ import annotations

import json
import hashlib
import csv
import io
import os
import time
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs
from typing import Any

from mwangaza._foundation import foundation_status
from mwangaza.admin import (
    AdminValidationError,
    admin_repository_from_env,
)
from mwangaza.audit import AuditRepository
from mwangaza.config import ConfigurationError, load_settings, public_config_status
from mwangaza.data.scheduled_refresh import load_refresh_status
from mwangaza.exports import (
    build_visible_export,
    export_visible_csv,
    export_visible_json,
    safe_export_filename,
)
from mwangaza.gee.auth import check_gee_auth
from mwangaza.observability import (
    METRICS,
    bind_run_id,
    current_run_id,
    emit,
    readiness_status,
    reset_run_id,
    resolve_run_id,
)
from mwangaza.security import (
    RATE_LIMITER,
    SECURITY_HEADERS,
    SecurityRequestError,
    validate_body_contract,
    validate_request_target,
)
from mwangaza.regions import list_regions
from mwangaza.reports import (
    build_executive_report_context,
    build_report_records,
    render_executive_report_html,
    render_executive_report_pdf,
    safe_report_filename,
)
from mwangaza.services.dashboard_shell import (
    load_alert_history,
    load_dashboard_shell_data,
    load_materialized_dashboard_shell_data,
)
from mwangaza.services.drought_continuation import (
    DroughtContinuationServiceError,
    continuation_response,
    load_continuation_snapshot,
    unavailable_response,
)

API_SCHEMA_VERSION = "mwangaza.api.v1"
APP_VERSION = "1.0.0"
METHODOLOGY_VERSION = "mwangaza-methodology-v1"
DEMO_REFERENCE_DATE = "2026-07-15"
DEMO_SNAPSHOT_ID = "mwangaza-offline-demo-v1"
MAX_LIMIT = 100
LIVE_DASHBOARD_CACHE_SECONDS = 120
_DASHBOARD_CACHE: tuple[float, Any] | None = None


@dataclass(frozen=True)
class RawResponse:
    body: bytes
    content_type: str
    filename: str


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
            payload["gee"] = {
                "status": "not_initialized",
                "message": "Disabled in explicit demo mode",
            }
            payload.update(_demo_metadata())
        else:
            payload["gee"] = check_gee_auth().to_public_dict()
        payload["observability"] = {"run_id": current_run_id(), "status": "ok"}
        gee_payload = payload["gee"]
        gee_status = (
            gee_payload.get("status", "unknown") if isinstance(gee_payload, dict) else "unknown"
        )
        _log("health checked", gee_status=gee_status)
        await _send_json(send, payload, HTTPStatus.OK)
        _log(
            "request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started)
        )
        return
    if path == "/ready":
        readiness = readiness_status()
        status = HTTPStatus.OK if readiness.ready else HTTPStatus.SERVICE_UNAVAILABLE
        await _send_json(send, readiness.to_public_dict() | {"run_id": current_run_id()}, status)
        _log("readiness checked", status=status, checks=readiness.checks)
        return
    if path == "/openapi.json":
        await _send_json(send, _openapi(), HTTPStatus.OK)
        _log(
            "request end", path=path, status=HTTPStatus.OK, elapsed_ms=_elapsed_ms(request_started)
        )
        return
    if path.startswith("/api/v1/"):
        try:
            body = await _read_body(receive)
            validate_body_contract(path, body, _header(scope.get("headers", []), "content-type"))
            payload, status, cache_seconds = _route_v1(
                path,
                scope.get("query_string", b""),
                scope.get("headers", []),
                body,
                method=str(scope.get("method", "GET")),
            )
            if _is_demo_mode() and isinstance(payload, dict):
                payload.update(_demo_metadata())
            if isinstance(payload, RawResponse):
                await _send_bytes(send, payload, status)
            else:
                await _send_json(send, payload, status, cache_seconds=cache_seconds)
            _log(
                "request end",
                path=path,
                status=status,
                elapsed_ms=_elapsed_ms(request_started),
                summary=_payload_summary(path, payload)
                if isinstance(payload, dict)
                else f"download={payload.filename}",
            )
        except SecurityRequestError:
            raise
        except AdminValidationError as exc:
            METRICS.record_error()
            await _send_json(
                send,
                {
                    "error": {
                        "code": "admin_validation_failed",
                        "message": "Configuration is invalid",
                        "details": exc.errors,
                    }
                },
                HTTPStatus.BAD_REQUEST,
            )
            _log(
                "request error",
                path=path,
                status=HTTPStatus.BAD_REQUEST,
                error="admin_validation_failed",
                elapsed_ms=_elapsed_ms(request_started),
            )
        except ValueError as exc:
            METRICS.record_error()
            await _send_json(send, _error("invalid_request", str(exc)), HTTPStatus.BAD_REQUEST)
            _log(
                "request error",
                path=path,
                status=HTTPStatus.BAD_REQUEST,
                error=str(exc),
                elapsed_ms=_elapsed_ms(request_started),
            )
        except Exception:
            METRICS.record_error()
            await _send_json(
                send,
                _error("internal_error", "Request could not be served"),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            _log(
                "request error",
                path=path,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                error="internal_error",
                elapsed_ms=_elapsed_ms(request_started),
            )
        return
    else:
        await _send_json(
            send,
            _error("not_found", "Use /health or /api/v1 endpoints."),
            HTTPStatus.NOT_FOUND,
        )
        _log(
            "request end",
            path=path,
            status=HTTPStatus.NOT_FOUND,
            elapsed_ms=_elapsed_ms(request_started),
        )
        return


def _route_v1(
    path: str,
    query_string: bytes,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
    method: str = "GET",
) -> tuple[dict[str, Any] | RawResponse, HTTPStatus, int | None]:
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
            source=export.source_metadata.get(
                "data_source", export.source_metadata.get("source", "unknown")
            ),
        )
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "data_mode": data.data_status.mode,
                "refresh": _public_refresh_status(data.data_status.mode),
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
            },
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/drought-continuation-probabilities":
        if method.upper() != "GET":
            raise ValueError("drought continuation endpoint is read-only")
        limit, offset = _pagination(query)
        region_id = _single_query(query, "region_id", "").strip()
        if region_id and (
            len(region_id) > 80
            or any(not (character.isalnum() or character in "-_") for character in region_id)
        ):
            raise ValueError("region_id is invalid")
        as_of = _single_query(query, "as_of", "").strip()
        if as_of:
            try:
                datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("as_of must be an ISO date or timestamp") from exc
        horizon_value = _single_query(query, "horizon_days", "").strip()
        horizon_days = None
        if horizon_value:
            try:
                horizon_days = int(horizon_value)
            except ValueError as exc:
                raise ValueError("horizon_days must be an integer") from exc
            if horizon_days not in {30, 60, 90, 180}:
                raise ValueError("horizon_days must be 30, 60, 90 or 180")
        try:
            snapshot = load_continuation_snapshot()
            response = continuation_response(
                snapshot,
                region_id=region_id or None,
                as_of=as_of or None,
                horizon_days=horizon_days,
                limit=limit,
                offset=offset,
            )
        except DroughtContinuationServiceError:
            response = unavailable_response("snapshot_unavailable", limit=limit, offset=offset)
        return {"schema_version": API_SCHEMA_VERSION} | response, HTTPStatus.OK, 60
    if path == "/api/v1/about/status":
        data = _load_api_dashboard_data()
        export = build_visible_export(data, max_rows=1)
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "app_version": APP_VERSION,
                "methodology_version": METHODOLOGY_VERSION,
                "data_mode": data.data_status.mode,
                "snapshot_id": export.source_metadata.get("snapshot_id"),
                "snapshot_updated_at": export.source_metadata.get("generated_at")
                or export.source_metadata.get("reference_date")
                or export.period,
                "documentation_status": _documentation_status(data.data_status.mode),
                "documentation_updated_at": "2026-07-23",
                "license": {"name": "MIT", "path": "/LICENSE"},
                "repository": {
                    "label": "Mwangaza source repository",
                    "url": os.environ.get("MWANGAZA_PUBLIC_REPOSITORY_URL"),
                },
                "contact": {
                    "label": "Project contact",
                    "url": os.environ.get("MWANGAZA_PUBLIC_CONTACT_URL"),
                },
                "refresh": _public_refresh_status(data.data_status.mode),
            },
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/reports":
        data = _load_api_dashboard_data()
        records = _filter_reports(list(build_report_records(data)), query)
        limit, offset = _pagination(query)
        if method.upper() == "POST":
            request = (
                _json_body(body)
                if body
                else {
                    name: _single_query(query, name, "")
                    for name in ("region_id", "period", "template_id", "language")
                }
            )
            region_id = str(request.get("region_id", "")).lower()
            template_id = str(request.get("template_id", "executive-v1") or "executive-v1")
            language = str(request.get("language", "en") or "en").lower()
            period = str(request.get("period", ""))
            if template_id != "executive-v1":
                raise ValueError("template_id must be executive-v1")
            if language not in {"en", "sw", "so", "es"}:
                raise ValueError("language is invalid")
            record = next(
                (item for item in records if not region_id or item.region_id == region_id), None
            )
            if record is None:
                raise ValueError("region_id is invalid or unavailable")
            if period and period not in {
                record.period_start,
                record.period_end,
                f"{record.period_start[:10]} to {record.period_end[:10]}",
            }:
                raise ValueError("period does not match the materialized snapshot")
            _record_report_audit("report_generated", record, format_name="record")
            return (
                {"schema_version": API_SCHEMA_VERSION, "report": record.to_dict()},
                HTTPStatus.CREATED,
                None,
            )
        items = [record.to_dict() for record in records]
        response = _listed(items, limit, offset)
        response["summary"] = {
            "ready": sum(item["status"] == "ready" for item in items),
            "generating": sum(item["status"] in {"queued", "generating"} for item in items),
            "failed": sum(item["status"] == "failed" for item in items),
            "expired": sum(item["status"] == "expired" for item in items),
        }
        return response, HTTPStatus.OK, 60
    if path.startswith("/api/v1/reports/") and path.endswith("/download"):
        report_id = path.removeprefix("/api/v1/reports/").removesuffix("/download").strip("/")
        data = _load_api_dashboard_data()
        record = next((item for item in build_report_records(data) if item.id == report_id), None)
        if record is None:
            return _error("not_found", "Report does not exist"), HTTPStatus.NOT_FOUND, 30
        if record.status in {"queued", "generating"}:
            return (
                _error("report_not_ready", "Report generation is still in progress"),
                HTTPStatus.CONFLICT,
                None,
            )
        if record.status == "failed":
            return (
                _error("report_failed", "Report generation failed"),
                HTTPStatus.UNPROCESSABLE_ENTITY,
                None,
            )
        if record.status == "expired":
            return _error("report_expired", "Report has expired"), HTTPStatus.GONE, None
        export_format = _single_query(query, "format", "pdf").lower()
        if export_format not in record.formats:
            raise ValueError("format must be pdf, csv or json")
        context = build_executive_report_context(
            data, region_id=record.region_id, dashboard_url=os.environ.get("MWANGAZA_DASHBOARD_URL")
        )
        export = build_visible_export(
            data, region_id=record.region_id, max_rows=MAX_LIMIT, include_geometry=False
        )
        if export_format == "pdf":
            payload = RawResponse(
                render_executive_report_pdf(context),
                "application/pdf",
                safe_report_filename(context),
            )
        elif export_format == "csv":
            payload = RawResponse(
                export_visible_csv(export).encode("utf-8"),
                "text/csv; charset=utf-8",
                safe_export_filename(export, "csv"),
            )
        else:
            payload = RawResponse(
                export_visible_json(export).encode("utf-8"),
                "application/json",
                safe_export_filename(export, "json"),
            )
        _record_report_audit("report_downloaded", record, format_name=export_format)
        return payload, HTTPStatus.OK, None
    if path.startswith("/api/v1/reports/") and path not in {
        "/api/v1/reports/alerts",
        "/api/v1/reports/executive",
    }:
        report_id = path.removeprefix("/api/v1/reports/")
        data = _load_api_dashboard_data()
        record = next((item for item in build_report_records(data) if item.id == report_id), None)
        if record is None:
            return _error("not_found", "Report does not exist"), HTTPStatus.NOT_FOUND, 30
        context = build_executive_report_context(data, region_id=record.region_id)
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "report": record.to_dict(),
                "events": _report_audit_events(record.id),
                "preview": {"format": "html", "content": render_executive_report_html(context)},
            },
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/alerts":
        limit, offset = _pagination(query)
        data = _load_api_dashboard_data()
        filtered = _filter_alerts(_all_alerts(data), query)
        alerts = [_alert_payload(alert) for alert in filtered]
        _log(
            "alerts export",
            data_mode=data.data_status.mode,
            total=len(alerts),
            limit=limit,
            offset=offset,
        )
        METRICS.observe_workload(active_alerts=len(alerts))
        response = _listed(alerts, limit, offset)
        response["summary"] = _alert_summary(alerts)
        return response, HTTPStatus.OK, 60
    if path.startswith("/api/v1/alerts/"):
        alert_id = path.removeprefix("/api/v1/alerts/")
        data = _load_api_dashboard_data()
        match = next(
            (alert for alert in _all_alerts(data) if _stable_alert_id(alert) == alert_id), None
        )
        if match is None:
            return _error("not_found", "Alert does not exist"), HTTPStatus.NOT_FOUND, 30
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "alert": _alert_payload(match),
            },
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/exports/alerts":
        data = _load_api_dashboard_data()
        alerts = [_alert_payload(alert) for alert in _filter_alerts(_all_alerts(data), query)]
        export_format = _single_query(query, "format", "csv").lower()
        if export_format == "csv":
            body = _alerts_csv(alerts)
            content_type = "text/csv; charset=utf-8"
        elif export_format == "json":
            body = json.dumps(
                {"schema_version": API_SCHEMA_VERSION, "items": alerts},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            content_type = "application/json"
        else:
            raise ValueError("format must be csv or json")
        return (
            RawResponse(
                body=body, content_type=content_type, filename=f"mwangaza-alerts.{export_format}"
            ),
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/reports/alerts":
        data = _load_api_dashboard_data()
        alerts = [_alert_payload(alert) for alert in _filter_alerts(_all_alerts(data), query)]
        return (
            RawResponse(
                body=_alerts_pdf(alerts),
                content_type="application/pdf",
                filename="mwangaza-alerts.pdf",
            ),
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/reports/executive":
        data = _load_api_dashboard_data()
        region_id, requested_period = _download_context(query, data)
        context = build_executive_report_context(
            data,
            region_id=region_id,
            dashboard_url=os.environ.get("MWANGAZA_DASHBOARD_URL"),
        )
        _require_matching_period(requested_period, context.period_label)
        return (
            RawResponse(
                body=render_executive_report_pdf(context),
                content_type="application/pdf",
                filename=safe_report_filename(context),
            ),
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/exports/snapshot":
        data = _load_api_dashboard_data()
        region_id, requested_period = _download_context(query, data)
        export = build_visible_export(
            data, region_id=region_id, max_rows=MAX_LIMIT, include_geometry=False
        )
        _require_matching_period(requested_period, export.period)
        export_format = _single_query(query, "format", "json").lower()
        if export_format == "csv":
            body = export_visible_csv(export).encode("utf-8")
            content_type = "text/csv; charset=utf-8"
        elif export_format == "json":
            body = export_visible_json(export).encode("utf-8")
            content_type = "application/json"
        else:
            raise ValueError("format must be csv or json")
        return (
            RawResponse(
                body=body,
                content_type=content_type,
                filename=safe_export_filename(export, export_format),
            ),
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/forecasts":
        limit, offset = _pagination(query)
        return (
            _listed([], limit, offset)
            | {"available": False, "message": "Forecasts are not available yet"},
            HTTPStatus.OK,
            60,
        )
    if path == "/api/v1/observability":
        readiness = readiness_status()
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "run_id": current_run_id(),
                "status": "operational" if readiness.ready else "degraded",
                "readiness": readiness.to_public_dict(),
                "metrics": METRICS.snapshot(),
            },
            HTTPStatus.OK,
            None,
        )
    if path == "/api/v1/admin/config":
        repo = admin_repository_from_env()
        try:
            if body:
                payload = _json_body(body)
                version = repo.create_version(
                    payload.get("configuration", {}),
                    actor="public-admin",
                    activate=bool(payload.get("activate", False)),
                )
                return _admin_payload(repo, version=version), HTTPStatus.CREATED, None
            return _admin_payload(repo), HTTPStatus.OK, None
        finally:
            repo.close()
    if path == "/api/v1/admin/config/activate":
        payload = _json_body(body)
        repo = admin_repository_from_env()
        try:
            version = repo.activate_version(
                str(payload.get("version_id", "")), actor="public-admin"
            )
            return _admin_payload(repo, version=version), HTTPStatus.OK, None
        finally:
            repo.close()
    if path == "/api/v1/admin/status":
        return (
            {
                "schema_version": API_SCHEMA_VERSION,
                "admin": {
                    "access": "public",
                    "auth": "none",
                    "institutional_auth": False,
                },
            },
            HTTPStatus.OK,
            None,
        )
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


def _stable_alert_id(alert: Any) -> str:
    supplied = str(getattr(alert, "alert_id", "") or "").strip()
    if supplied:
        return supplied
    region_id = str(getattr(alert, "region_id", "") or "region").lower()
    identity = "|".join(
        (
            region_id,
            str(getattr(alert, "title", "")),
            str(getattr(alert, "period", "")),
            str(getattr(alert, "status", "")),
        )
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"ALT-{region_id.upper()}-{digest.upper()}"


def _alert_payload(alert: Any) -> dict[str, Any]:
    alert_id = _stable_alert_id(alert)
    issued_at = str(
        getattr(alert, "issued_at", "")
        or getattr(alert, "period_start", "")
        or getattr(alert, "period", "")
    )
    updated_at = str(
        getattr(alert, "updated_at", "") or getattr(alert, "period_end", "") or issued_at
    )
    events = list(getattr(alert, "events", ()) or ())
    if not events:
        events = [
            {
                "event_type": "triggered",
                "status": "active",
                "created_at": issued_at,
                "from_severity": None,
                "to_severity": alert.severity,
                "metadata": {},
            },
            {
                "event_type": "status_observed",
                "status": alert.status,
                "created_at": updated_at,
                "from_severity": alert.severity,
                "to_severity": alert.severity,
                "metadata": {},
            },
        ]
    recommendations = list(getattr(alert, "recommendations", ()) or ())
    if not recommendations:
        recommendations = [
            {
                "action": alert.recommended_action or alert.action,
                "suggested_actor": None,
                "urgency": _alert_urgency(alert.severity),
                "horizon": None,
                "evidence": {
                    "region_id": alert.region_id,
                    "score": alert.score,
                    "quality_flag": alert.quality_flag,
                },
                "recommendation_version": None,
            }
        ]
    return {
        "id": alert_id,
        "region_id": alert.region_id,
        "region": alert.region,
        "severity": alert.severity,
        "status": alert.status,
        "title": alert.title,
        "period": alert.period,
        "period_start": alert.period_start,
        "period_end": alert.period_end,
        "issued_at": issued_at,
        "updated_at": updated_at,
        "resolved_at": getattr(alert, "resolved_at", None),
        "alert_type": getattr(alert, "alert_type", "drought"),
        "quality_flag": alert.quality_flag,
        "score": alert.score,
        "evidence": [{"label": label, "value": value} for label, value in alert.evidence],
        "recommended_action": alert.recommended_action or alert.action,
        "recommendations": recommendations,
        "events": events,
        "notifications": _simulated_notifications(alert, alert_id),
    }


def _alert_urgency(severity: str) -> str:
    return {
        "critical": "urgent_activation",
        "warning": "prepositioning",
        "watch": "preparation",
    }.get(severity, "monitoring")


def _simulated_notifications(alert: Any, alert_id: str) -> list[dict[str, Any]]:
    recipients = (
        ("sms", "***0000"),
        ("email", "op***@example.org"),
        ("telegram", "@m***"),
        ("dashboard", "authenticated users"),
    )
    return [
        {
            "id": hashlib.sha256(f"{alert_id}|{channel}".encode("utf-8")).hexdigest()[:12],
            "channel": channel,
            "recipient_masked": recipient,
            "content": f"[SIMULATED] {alert.region}: {alert.title}",
            "status": "simulated",
            "created_at": str(
                getattr(alert, "updated_at", "")
                or getattr(alert, "period_end", "")
                or getattr(alert, "period", "")
            ),
            "is_simulated": True,
        }
        for channel, recipient in recipients
    ]


def _filter_alerts(alerts: list[Any], query: dict[str, list[str]]) -> list[Any]:
    filters = {
        name: _single_query(query, name, "").lower()
        for name in ("q", "region", "severity", "status", "period")
    }
    valid_severity = {"normal", "watch", "warning", "critical", "unknown"}
    valid_status = {"preventive", "active", "monitoring", "resolved", "superseded"}
    if filters["severity"] and filters["severity"] not in valid_severity:
        raise ValueError("severity is invalid")
    if filters["status"] and filters["status"] not in valid_status:
        raise ValueError("status is invalid")
    result: list[Any] = []
    for alert in alerts:
        searchable = " ".join(
            (
                _stable_alert_id(alert),
                str(alert.region),
                str(alert.title),
                str(alert.action),
                str(alert.quality_flag),
                str(alert.evidence),
            )
        ).lower()
        if filters["q"] and filters["q"] not in searchable:
            continue
        if filters["region"] and filters["region"] != str(alert.region_id).lower():
            continue
        if filters["severity"] and filters["severity"] != str(alert.severity).lower():
            continue
        if filters["status"] and filters["status"] != str(alert.status).lower():
            continue
        period_values = " ".join(
            (str(alert.period), str(alert.period_start), str(alert.period_end))
        ).lower()
        if filters["period"] and filters["period"] not in period_values:
            continue
        result.append(alert)
    return result


def _filter_reports(reports: list[Any], query: dict[str, list[str]]) -> list[Any]:
    filters = {
        name: _single_query(query, name, "").lower()
        for name in ("q", "region", "type", "period", "status")
    }
    valid_status = {"queued", "generating", "ready", "failed", "expired"}
    if filters["status"] and filters["status"] not in valid_status:
        raise ValueError("status is invalid")
    result: list[Any] = []
    for report in reports:
        searchable = " ".join(
            (report.id, report.region_id, report.region, report.template_id, report.language)
        ).lower()
        period = f"{report.period_start} {report.period_end}".lower()
        if filters["q"] and filters["q"] not in searchable:
            continue
        if filters["region"] and filters["region"] != report.region_id:
            continue
        if filters["type"] and filters["type"] != report.template_id.lower():
            continue
        if filters["period"] and filters["period"] not in period:
            continue
        if filters["status"] and filters["status"] != report.status:
            continue
        result.append(report)
    return result


def _record_report_audit(event_type: str, report: Any, *, format_name: str) -> None:
    path = Path(os.environ.get("MWANGAZA_AUDIT_DB_PATH", "data/audit.sqlite"))
    repo: AuditRepository | None = None
    try:
        repo = AuditRepository(path)
        repo.record_event(
            actor="public-dashboard",
            event_type=event_type,
            entity_type="report",
            entity_id=report.id,
            region_id=report.region_id,
            run_id=current_run_id(),
            snapshot_id=report.snapshot_id,
            metadata={"format": format_name, "template_id": report.template_id},
        )
    except Exception:
        _log(
            "report audit unavailable", level="WARNING", report_id=report.id, event_type=event_type
        )
    finally:
        if repo is not None:
            repo.close()


def _report_audit_events(report_id: str) -> list[dict[str, Any]]:
    path = Path(os.environ.get("MWANGAZA_AUDIT_DB_PATH", "data/audit.sqlite"))
    if not path.is_file():
        return []
    repo: AuditRepository | None = None
    try:
        repo = AuditRepository(path)
        events = (
            *repo.list_events(event_type="report_generated"),
            *repo.list_events(event_type="report_downloaded"),
        )
        return [event.__dict__ for event in events if event.entity_id == report_id]
    except Exception:
        return []
    finally:
        if repo is not None:
            repo.close()


def _all_alerts(data: Any) -> list[Any]:
    if getattr(getattr(data, "data_status", None), "mode", "") == "demo":
        return list(data.alerts)
    persisted = list(load_alert_history())
    if not persisted:
        return list(data.alerts)
    by_id = {_stable_alert_id(alert): alert for alert in persisted}
    for alert in data.alerts:
        by_id.setdefault(_stable_alert_id(alert), alert)
    return sorted(
        by_id.values(),
        key=lambda alert: (
            str(alert.status) not in {"active", "preventive"},
            getattr(alert, "priority_rank", 999),
            _stable_alert_id(alert),
        ),
    )


def _alert_summary(alerts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "active": sum(item["status"] == "active" for item in alerts),
        "severe": sum(item["severity"] == "critical" for item in alerts),
        "preventive": sum(item["status"] == "preventive" for item in alerts),
        "resolved": sum(item["status"] == "resolved" for item in alerts),
        "superseded": sum(item["status"] == "superseded" for item in alerts),
        "notifications_simulated": sum(len(item["notifications"]) for item in alerts),
    }


def _alerts_csv(alerts: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    fields = (
        "id",
        "region_id",
        "region",
        "severity",
        "status",
        "alert_type",
        "issued_at",
        "updated_at",
        "resolved_at",
        "score",
        "quality_flag",
        "title",
        "recommended_action",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(alerts)
    return stream.getvalue().encode("utf-8")


def _alerts_pdf(alerts: list[dict[str, Any]]) -> bytes:
    rows = "\n".join(
        f"{item['id']} | {item['region']} | {item['severity']} | {item['status']} | {item['title']}"
        for item in alerts
    )
    return f"%PDF-HTML\nMwangaza filtered alerts\n{rows}\n".encode("utf-8")


def _download_context(query: dict[str, list[str]], data: Any) -> tuple[str, str]:
    region_id = _single_query(query, "region", str(getattr(data, "selected_region_id", ""))).lower()
    available = {str(profile.region_id).lower() for profile in getattr(data, "region_profiles", ())}
    if region_id not in available:
        raise ValueError("region is not available in the loaded snapshot")
    return region_id, _single_query(query, "period", "")


def _single_query(query: dict[str, list[str]], name: str, default: str) -> str:
    values = query.get(name)
    if not values:
        return default
    value = str(values[0]).strip()
    if not value or len(value) > 160:
        raise ValueError(f"{name} is invalid")
    return value


def _require_matching_period(requested: str, actual: str) -> None:
    if requested and requested != actual:
        raise ValueError("period is not available for the selected region")


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
            raise SecurityRequestError(
                "payload_too_large",
                "Request body exceeds 64 KiB",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
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
    mode = (
        "demo"
        if configured == "demo"
        else os.environ.get("MWANGAZA_API_DATA_MODE", default_mode).strip().lower()
    )
    _log("dashboard load requested", configured_mode=mode or "demo")
    if mode in {"live", "auto"}:
        return _cached_live_dashboard_data()
    if mode == "cache":
        data = load_materialized_dashboard_shell_data()
        if data is None:
            raise RuntimeError("materialized cache unavailable")
        return data
    data = load_dashboard_shell_data("demo")
    _log("dashboard load complete", selected_mode="demo", data_mode=data.data_status.mode)
    return data


def _is_demo_mode() -> bool:
    return os.environ.get("MWANGAZA_MODE", "").strip().lower() == "demo"


def _demo_metadata() -> dict[str, Any]:
    return {
        "data_mode": "demo",
        "is_demo": True,
        "reference_date": DEMO_REFERENCE_DATE,
        "snapshot_id": DEMO_SNAPSHOT_ID,
    }


def _cached_live_dashboard_data() -> Any:
    global _DASHBOARD_CACHE
    now = time.monotonic()
    if _DASHBOARD_CACHE is not None:
        cached_at, data = _DASHBOARD_CACHE
        age_seconds = now - cached_at
        if age_seconds < LIVE_DASHBOARD_CACHE_SECONDS:
            METRICS.record_cache(True)
            _log(
                "dashboard cache hit", age_s=round(age_seconds, 2), data_mode=data.data_status.mode
            )
            return data
        _log("dashboard cache expired", age_s=round(age_seconds, 2))
    materialized = load_materialized_dashboard_shell_data()
    if materialized is not None:
        _DASHBOARD_CACHE = (now, materialized)
        METRICS.record_cache(True)
        _log("dashboard materialized response served", data_mode=materialized.data_status.mode)
        return materialized
    METRICS.record_cache(False)
    raise RuntimeError("scheduled materialized snapshot unavailable")


def _public_refresh_status(data_mode: str) -> dict[str, Any]:
    if data_mode == "demo":
        return {
            "kind": "none",
            "state": "not_applicable",
            "gee_triggered": False,
            "writes_performed": False,
            "last_attempt": None,
            "last_success": None,
        }
    try:
        refresh_cache_dir = os.environ.get("MWANGAZA_REFRESH_CACHE_DIR", "").strip()
        cache_dir = Path(refresh_cache_dir) if refresh_cache_dir else load_settings().cache_dir
    except ConfigurationError:
        status: dict[str, Any] = {}
    else:
        status = load_refresh_status(cache_dir)

    def public_run(value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        allowed = (
            "run_id",
            "period",
            "status",
            "started_at",
            "finished_at",
            "query_generated_at",
            "effective_observation_at",
            "age_days",
            "freshness",
            "stale_after_days",
            "quality_summary",
            "message",
        )
        return {key: value[key] for key in allowed if key in value}

    return {
        "kind": "scheduled_materialization",
        "state": status.get("state", "unavailable"),
        "gee_triggered": False,
        "writes_performed": False,
        "last_attempt": public_run(status.get("last_attempt")),
        "last_success": public_run(status.get("last_success")),
    }


def _documentation_status(data_mode: str) -> str:
    state = _public_refresh_status(data_mode)["state"]
    return "stale" if state in {"stale", "failed", "unavailable"} else "current"


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
        "/api/v1/drought-continuation-probabilities": {
            "region_id": "adm1-ke-43",
            "horizon_days": 30,
            "estimate_kinds": ["experimental_ml_prediction", "historical_reference"],
        },
        "/api/v1/about/status": {
            "app_version": APP_VERSION,
            "methodology_version": METHODOLOGY_VERSION,
        },
        "/api/v1/alerts": {"limit": 10, "offset": 0},
        "/api/v1/alerts/{alert_id}": {"alert_id": "ALT-SOM-EXAMPLE"},
        "/api/v1/exports/alerts": {
            "region": "som",
            "severity": "critical",
            "status": "active",
            "format": "csv",
        },
        "/api/v1/reports/alerts": {"region": "som", "severity": "critical", "status": "active"},
        "/api/v1/reports": {"limit": 20, "offset": 0, "region": "som", "status": "ready"},
        "/api/v1/reports/{report_id}": {"report_id": "RPT-SOM-EXAMPLE"},
        "/api/v1/reports/{report_id}/download": {"report_id": "RPT-SOM-EXAMPLE", "format": "pdf"},
        "/api/v1/forecasts": {"available": False},
        "/api/v1/reports/executive": {"region": "som", "period": "2026-07-01 to 2026-07-15"},
        "/api/v1/exports/snapshot": {
            "region": "som",
            "period": "2026-07-01 to 2026-07-15",
            "format": "csv",
        },
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
            "/ready": {
                "get": {
                    "responses": {
                        "200": {"description": "Ready"},
                        "503": {"description": "Not ready"},
                    }
                }
            },
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
    headers = [
        (b"content-type", b"application/json"),
        (b"x-run-id", current_run_id().encode("ascii")),
    ]
    headers.extend(
        (name.encode("ascii"), value.encode("ascii")) for name, value in SECURITY_HEADERS.items()
    )
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


async def _send_bytes(send: Any, payload: RawResponse, status: HTTPStatus) -> None:
    filename = payload.filename.encode("ascii", errors="ignore").decode("ascii")
    headers = [
        (b"content-type", payload.content_type.encode("ascii")),
        (b"content-disposition", f'attachment; filename="{filename}"'.encode("ascii")),
        (b"content-length", str(len(payload.body)).encode("ascii")),
        (b"x-content-type-options", b"nosniff"),
        (b"x-run-id", current_run_id().encode("ascii")),
    ]
    headers.extend(
        (name.encode("ascii"), value.encode("ascii"))
        for name, value in SECURITY_HEADERS.items()
        if name.lower() != "x-content-type-options"
    )
    await send({"type": "http.response.start", "status": int(status), "headers": headers})
    await send({"type": "http.response.body", "body": payload.body})


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
    if path == "/api/v1/drought-continuation-probabilities":
        return (
            f"availability={payload.get('availability')} total={payload.get('total')} "
            f"returned={len(payload.get('items', []))}"
        )
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

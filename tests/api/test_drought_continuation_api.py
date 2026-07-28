from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

from mwangaza.api.app import app


def test_30_day_api_returns_ml_and_reference_with_cache() -> None:
    with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
        status, headers, payload = _request(b"region_id=adm1-ke-43&horizon_days=30")

    assert status == 200
    assert headers["cache-control"] == "public, max-age=60"
    assert payload["schema_version"] == "mwangaza.api.v1"
    assert payload["total"] == 1
    estimates = payload["items"][0]["estimates"]
    assert [item["kind"] for item in estimates] == [
        "experimental_ml_prediction",
        "historical_reference",
    ]
    assert estimates[0]["validation"]["status"] == "inconclusive"
    assert estimates[0]["operational_use"] is False


def test_long_horizon_is_baseline_only_and_inactive_is_not_applicable() -> None:
    with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
        long_status, _headers, long_payload = _request(b"region_id=adm1-ke-43&horizon_days=180")
        inactive_status, _headers, inactive_payload = _request(
            b"region_id=adm1-ke-01&horizon_days=30"
        )

    assert long_status == inactive_status == 200
    assert [item["kind"] for item in long_payload["items"][0]["estimates"]] == [
        "historical_reference"
    ]
    assert inactive_payload["items"][0]["status"] == "not_applicable"
    assert inactive_payload["items"][0]["estimates"] == []


def test_api_validates_filters_and_pagination() -> None:
    with patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}):
        invalid_status, _headers, invalid = _request(b"horizon_days=31")
        page_status, _headers, page = _request(b"limit=2&offset=1")
        date_status, _headers, dated = _request(
            b"region_id=adm1-ke-43&as_of=2026-04-30&horizon_days=30"
        )

    assert invalid_status == 400
    assert invalid["error"]["code"] == "invalid_request"
    assert page_status == 200
    assert len(page["items"]) == 2
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert date_status == 200
    assert dated["total"] == 1


def test_openapi_documents_drought_continuation_endpoint() -> None:
    status, _headers, payload = _request(path="/openapi.json")

    assert status == 200
    assert "/api/v1/drought-continuation-probabilities" in payload["paths"]
    example = payload["paths"]["/api/v1/drought-continuation-probabilities"]["get"]["x-example"]
    assert example["estimate_kinds"] == [
        "experimental_ml_prediction",
        "historical_reference",
    ]


def test_request_does_not_train_or_call_gee() -> None:
    with (
        patch.dict(os.environ, {"MWANGAZA_API_DATA_MODE": "demo"}),
        patch("mwangaza.probabilistic.ml_sanity_audit.fit_hazard") as train,
        patch("mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads") as gee,
    ):
        status, _headers, _payload = _request(b"horizon_days=30")

    assert status == 200
    train.assert_not_called()
    gee.assert_not_called()


def test_missing_snapshot_is_safe_unavailable() -> None:
    with patch.dict(
        os.environ,
        {"MWANGAZA_DROUGHT_CONTINUATION_SNAPSHOT": "missing-snapshot.json"},
    ):
        status, _headers, payload = _request()

    assert status == 200
    assert payload["availability"] == "unavailable"
    assert payload["reason_codes"] == ["snapshot_unavailable"]
    assert payload["items"] == []


def _request(
    query: bytes = b"",
    *,
    path: str = "/api/v1/drought-continuation-probabilities",
) -> tuple[int, dict[str, str], dict[str, object]]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "path": path,
                "query_string": query,
                "method": "GET",
            },
            receive,
            send,
        )
    )
    headers = {
        key.decode("ascii"): value.decode("ascii")
        for key, value in messages[0].get("headers", [])  # type: ignore[union-attr]
    }
    return (
        int(messages[0]["status"]),
        headers,
        json.loads(messages[1]["body"]),  # type: ignore[arg-type]
    )

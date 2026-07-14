from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from mwangaza._foundation import foundation_status
from mwangaza.config import public_config_status
from mwangaza.gee.auth import check_gee_auth


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    if path == "/health":
        payload = foundation_status().as_dict() | public_config_status()
        payload["gee"] = check_gee_auth().to_public_dict()
        body = json.dumps(payload).encode("utf-8")
        status = HTTPStatus.OK
    else:
        body = json.dumps(
            {
                "project": "Mwangaza",
                "status": "foundation stub",
                "detail": "Use /health for the Sprint 0 health contract.",
            }
        ).encode("utf-8")
        status = HTTPStatus.NOT_FOUND

    await send(
        {
            "type": "http.response.start",
            "status": int(status),
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mwangaza.cache import AnalyticalCache, CacheConfig, build_cache_key
from mwangaza.gee.auth import check_gee_auth
from mwangaza.services.live_gee_dashboard import load_live_gee_dashboard_payloads

SENSITIVE_KEY_PARTS = ("private_key", "service_account", "token", "secret", "password")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sprint 23 smoke: query real GEE and seed dashboard cache."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("MWANGAZA_CACHE_DIR", ".cache/mwangaza")),
        help="Cache directory consumed by the dashboard.",
    )
    parser.add_argument("--region-id", default="som", help="Region ID to query and seed.")
    parser.add_argument("--period-start", default=None, help="ISO8601 analysis window start.")
    parser.add_argument("--period-end", default=None, help="ISO8601 analysis window end.")
    parser.add_argument("--scale", type=int, default=5500, help="Earth Engine reducer scale.")
    args = parser.parse_args(argv)

    auth = check_gee_auth()
    if auth.status != "ok":
        print(json.dumps({"gee": auth.to_public_dict(), "cache_written": False}, sort_keys=True))
        return 1

    payloads = load_live_gee_dashboard_payloads(
        region_id=args.region_id,
        period_start=args.period_start,
        period_end=args.period_end,
        scale_meters=args.scale,
    )
    findings = find_sensitive_content(payloads)
    if findings:
        print(json.dumps({"cache_written": False, "sensitive_findings": findings}, sort_keys=True))
        return 2

    cache = AnalyticalCache(CacheConfig(args.cache_dir, {"default": 7 * 24 * 3600}))
    written = []
    for payload in payloads:
        key = build_cache_key(
            region_id=args.region_id,
            indicator=str(payload.get("indicator", payload.get("payload_type", "risk"))),
            period_start=str(payload.get("period_start", "")),
            period_end=str(payload.get("period_end", "")),
            source=str(payload.get("source", "mwangaza.live_gee_dashboard")),
            algorithm_version="sprint23-live-gee-v1",
            data_type=str(payload.get("payload_type", "dashboard_payload")),
        )
        entry = cache.write(key, payload, now=datetime.now(UTC), metadata={"smoke_test": "sprint23"})
        written.append(entry.cache_key)

    print(
        json.dumps(
            {
                "gee": auth.to_public_dict(),
                "cache_written": True,
                "cache_dir": str(args.cache_dir),
                "entries": len(written),
                "source": "real_gee",
            },
            sort_keys=True,
        )
    )
    return 0


def find_sensitive_content(payloads: Any) -> list[str]:
    secret_values = _secret_values_from_env()
    findings: list[str] = []
    _scan(payloads, "$", secret_values, findings)
    return findings


def _scan(value: Any, path: str, secret_values: tuple[str, ...], findings: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                findings.append(f"{path}.{key}")
            _scan(item, f"{path}.{key}", secret_values, findings)
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _scan(item, f"{path}[{index}]", secret_values, findings)
    elif isinstance(value, str):
        for secret in secret_values:
            if secret and secret in value:
                findings.append(path)


def _secret_values_from_env() -> tuple[str, ...]:
    values = (
        os.environ.get("MWANGAZA_GEE_PROJECT", ""),
        os.environ.get("MWANGAZA_GEE_SERVICE_ACCOUNT", ""),
        os.environ.get("MWANGAZA_GEE_PRIVATE_KEY_JSON", ""),
    )
    return tuple(value for value in values if len(value) >= 8)


if __name__ == "__main__":
    raise SystemExit(main())

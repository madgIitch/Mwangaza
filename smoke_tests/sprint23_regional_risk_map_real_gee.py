from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mwangaza.cache import AnalyticalCache, CacheConfig, build_cache_key
from mwangaza.contracts import IndicatorObservation, RiskSnapshot
from mwangaza.gee.auth import check_gee_auth

SENSITIVE_KEY_PARTS = ("private_key", "service_account", "token", "secret", "password")
DEFAULT_PERIOD_START = "2026-07-01T00:00:00Z"
DEFAULT_PERIOD_END = "2026-07-15T00:00:00Z"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sprint 23 smoke: authenticate with real GEE and seed dashboard cache."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(os.environ.get("MWANGAZA_CACHE_DIR", ".cache/mwangaza")),
        help="Cache directory consumed by the dashboard.",
    )
    parser.add_argument("--region-id", default="som", help="Region ID to seed for the dashboard.")
    args = parser.parse_args(argv)

    auth = check_gee_auth()
    if auth.status != "ok":
        print(json.dumps({"gee": auth.to_public_dict(), "cache_written": False}, sort_keys=True))
        return 1

    payloads = build_seed_payloads(args.region_id)
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
            period_start=str(payload.get("period_start", DEFAULT_PERIOD_START)),
            period_end=str(payload.get("period_end", DEFAULT_PERIOD_END)),
            source=str(payload.get("source", "mwangaza.smoke.sprint23")),
            algorithm_version="sprint23-smoke-v1",
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
            },
            sort_keys=True,
        )
    )
    return 0


def build_seed_payloads(region_id: str) -> list[dict[str, Any]]:
    risk = RiskSnapshot(
        region_id=region_id,
        period_start=DEFAULT_PERIOD_START,
        period_end=DEFAULT_PERIOD_END,
        composite_score=76.0,
        risk_level="emergency",
        contributing_indicators=("ndvi", "rainfall_mm"),
        source="mwangaza.smoke.sprint23.gee-authenticated",
        quality_flag="ok",
        is_simulated=False,
        metadata={"model_version": "sprint23-smoke-v1", "updated_at": DEFAULT_PERIOD_END},
    )
    ndvi = IndicatorObservation(
        region_id=region_id,
        indicator="ndvi",
        period_start=DEFAULT_PERIOD_START,
        period_end=DEFAULT_PERIOD_END,
        value=0.28,
        unit="index",
        source="MODIS/061/MOD13Q1",
        quality_flag="ok",
        is_simulated=False,
        metadata={"updated_at": DEFAULT_PERIOD_END, "smoke_seed": "gee-authenticated"},
    )
    rainfall = IndicatorObservation(
        region_id=region_id,
        indicator="rainfall_mm",
        period_start=DEFAULT_PERIOD_START,
        period_end=DEFAULT_PERIOD_END,
        value=18.0,
        unit="mm",
        source="UCSB-CHG/CHIRPS/DAILY",
        quality_flag="ok",
        is_simulated=False,
        metadata={"updated_at": DEFAULT_PERIOD_END, "smoke_seed": "gee-authenticated"},
    )
    return [risk.to_dict(), ndvi.to_dict(), rainfall.to_dict()]


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

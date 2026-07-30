from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from mwangaza._foundation import foundation_status
from mwangaza.config import ConfigurationError, load_settings
from mwangaza.data.scheduled_refresh import (
    DEFAULT_STALE_AFTER_DAYS,
    FileRefreshStore,
    GcsRefreshStore,
    ScheduledRefreshError,
    run_scheduled_refresh,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mwangaza data refresh entrypoint.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the refresh entrypoint without remote service calls.",
    )
    parser.add_argument("--period", help="Logical processing period as YYYY-MM-DD (default: today UTC).")
    parser.add_argument("--run-id", help="Optional externally supplied run id.")
    parser.add_argument("--output-dir", type=Path, help="Override the materialized cache directory.")
    parser.add_argument("--gcs-bucket", help="Publish to Cloud Storage using generation preconditions.")
    parser.add_argument("--gcs-prefix", default="mwangaza-refresh")
    parser.add_argument("--stale-after-days", type=int, default=DEFAULT_STALE_AFTER_DAYS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = foundation_status()
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc))
        return 1

    period = args.period or datetime.now(UTC).date().isoformat()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "project": status.project,
                    "version": status.version,
                    "status": "dry_run",
                    "environment": settings.environment,
                    "period": period,
                    "remote_queries": 0,
                    "writes_performed": 0,
                },
                sort_keys=True,
            )
        )
        return 0

    try:
        bucket = args.gcs_bucket or os.environ.get("MWANGAZA_REFRESH_BUCKET", "").strip()
        store = GcsRefreshStore(bucket, prefix=args.gcs_prefix) if bucket else FileRefreshStore(
            args.output_dir or settings.cache_dir
        )
        result = run_scheduled_refresh(
            _real_gee_payloads,
            store,
            period=period,
            run_id=args.run_id,
            stale_after_days=args.stale_after_days,
        )
    except ScheduledRefreshError as exc:
        print(json.dumps({"status": "invalid", "message": str(exc)}, sort_keys=True))
        return 2
    event = result.to_dict() | {
        "component": "scheduled_refresh",
        "severity": "ERROR" if result.exit_code else "INFO",
    }
    print(json.dumps(event, sort_keys=True), file=sys.stderr if result.exit_code else sys.stdout)
    return result.exit_code


def _real_gee_payloads() -> tuple[dict[str, object], ...]:
    from mwangaza.services.live_gee_dashboard import load_live_gee_dashboard_payloads

    return tuple(load_live_gee_dashboard_payloads())


if __name__ == "__main__":
    raise SystemExit(main())

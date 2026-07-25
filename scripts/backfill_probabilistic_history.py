"""Download real regional history for the probabilistic pipeline."""

from __future__ import annotations

import argparse
import importlib
from datetime import date
from pathlib import Path

from mwangaza.gee.auth import check_gee_auth
from mwangaza.gee.historical import EarthEngineHistoricalAdapter
from mwangaza.probabilistic.backfill import (
    dekadal_windows,
    last_complete_dekad,
    materialize_history,
)
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.regions import COUNTRY_LEVEL, get_region, list_regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("kenya", "igad"), default="kenya")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=last_complete_dekad())
    parser.add_argument("--output", type=Path, default=Path("data/historical/gee-from-2024"))
    parser.add_argument("--chunk-size", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-remote", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    regions = (
        (get_region("ken"),)
        if args.scope == "kenya"
        else list_regions(level=COUNTRY_LEVEL, include_pilots=False)
    )
    windows = dekadal_windows(args.start, args.end)
    print(
        f"Plan: {len(regions)} regions x {len(windows)} dekads = "
        f"{len(regions) * len(windows)} rows"
    )
    print(f"Period: {windows[0].period_start} to {windows[-1].period_end}")
    print(f"Output: {args.output}")
    if args.dry_run:
        return
    if not args.confirm_remote:
        parser.error("remote extraction requires --confirm-remote")

    ee = importlib.import_module("ee")
    auth = check_gee_auth(ee_module=ee)
    if auth.status != "ok":
        parser.error(auth.message)
    manifest = materialize_history(
        regions=tuple(regions),
        windows=windows,
        adapter=EarthEngineHistoricalAdapter(ee),
        output_dir=args.output,
        chunk_size=args.chunk_size,
        force=args.force,
        progress=EtaProgress("GEE backfill"),
    )
    print(f"Rows: {manifest.row_count}")
    print(f"Missing signals: {manifest.missing_signal_count}")
    print(f"SHA-256: {manifest.data_sha256}")


if __name__ == "__main__":
    main()

"""Materialize leakage-safe antecedent drought signals for IGAD ADM1 regions."""

from __future__ import annotations

import argparse
import importlib
from datetime import date
from pathlib import Path

from mwangaza.gee.adm1_antecedent import EarthEngineAdm1AntecedentAdapter
from mwangaza.gee.auth import check_gee_auth
from mwangaza.probabilistic.adm1 import materialize_adm1_history
from mwangaza.probabilistic.backfill import dekadal_windows, last_complete_dekad
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.regions import ADM1_LEVEL, get_region, list_regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2003, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=last_complete_dekad())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/historical/adm1-antecedent-2003-current"),
    )
    parser.add_argument(
        "--region",
        action="append",
        default=[],
        help="ADM1 region id; repeat to run a smoke subset. Default: all 121 ADM1.",
    )
    parser.add_argument("--window-chunk-size", type=int, default=12)
    parser.add_argument("--region-batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-remote", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    regions = (
        tuple(get_region(region_id) for region_id in args.region)
        if args.region
        else list_regions(level=ADM1_LEVEL, include_administrative=True)
    )
    if not args.region and len(regions) != 121:
        parser.error(f"versioned ADM1 catalog must contain exactly 121 regions, got {len(regions)}")
    if any(region.level != ADM1_LEVEL for region in regions):
        parser.error("--region only accepts ADM1 region ids")
    windows = dekadal_windows(args.start, args.end)
    if not windows:
        parser.error("period contains no complete dekads")
    row_count = len(regions) * len(windows)
    remote_batches = (
        (len(regions) + args.region_batch_size - 1) // args.region_batch_size
    ) * ((len(windows) + args.window_chunk_size - 1) // args.window_chunk_size)
    print(f"Plan: {len(regions)} ADM1 x {len(windows)} dekads = {row_count} rows")
    print(f"Remote batches (maximum): {remote_batches}")
    print(f"Period: {windows[0].period_start} to {windows[-1].period_end}")
    print(f"Output: {args.output}")
    print("Sources: CHIRPS, MOD13Q1, SPEIbase 2.11, NASA FLDAS, ECMWF IFS")
    if args.dry_run:
        return
    if not args.confirm_remote:
        parser.error("remote extraction requires --confirm-remote")

    ee = importlib.import_module("ee")
    auth = check_gee_auth(ee_module=ee)
    if auth.status != "ok":
        parser.error(auth.message)
    manifest = materialize_adm1_history(
        regions=regions,
        windows=windows,
        adapter=EarthEngineAdm1AntecedentAdapter(ee),
        output_dir=args.output,
        window_chunk_size=args.window_chunk_size,
        region_batch_size=args.region_batch_size,
        force=args.force,
        progress=EtaProgress("ADM1 GEE backfill"),
    )
    print(f"Rows: {manifest.row_count}")
    print(f"Regions: {manifest.region_count}")
    print(f"Missing signals: {manifest.missing_signal_count}")
    print(f"SHA-256: {manifest.data_sha256}")


if __name__ == "__main__":
    main()

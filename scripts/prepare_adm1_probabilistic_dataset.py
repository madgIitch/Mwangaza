"""Prepare ADM1 antecedent features without training or producing probabilities."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from mwangaza.probabilistic.adm1 import load_adm1_raw_rows, write_prepared_rows
from mwangaza.probabilistic.antecedents import prepare_adm1_antecedents
from mwangaza.probabilistic.progress import EtaProgress


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("data/historical/adm1-antecedent-2003-current/adm1-history.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/historical/adm1-probabilistic-features"),
    )
    parser.add_argument(
        "--reference-end",
        type=date.fromisoformat,
        default=date(2017, 12, 31),
        help="Last date allowed to fit SPI, rainfall and NDVI reference distributions.",
    )
    parser.add_argument("--min-reference-years", type=int, default=15)
    parser.add_argument(
        "--output-start",
        type=date.fromisoformat,
        default=date(2003, 1, 1),
        help="First period retained in the prepared artifact; earlier rows are warm-up only.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.history.exists():
        parser.error(
            f"history not found: {args.history}. Run backfill_adm1_antecedent_signals.py first."
        )
    rows = load_adm1_raw_rows(args.history)
    print(f"Input rows: {len(rows)}")
    print(f"Regions: {len({row.region_id for row in rows})}")
    print(f"Reference cutoff: {args.reference_end}")
    print(f"Publishable period starts: {args.output_start}")
    print(f"Output: {args.output}")
    if args.dry_run:
        return
    prepared = prepare_adm1_antecedents(
        rows,
        reference_end=args.reference_end,
        min_reference_years=args.min_reference_years,
        output_start=args.output_start,
        progress=EtaProgress("ADM1 data treatment"),
    )
    manifest = write_prepared_rows(prepared, args.output)
    print(f"Rows: {manifest['row_count']}")
    print(f"Regions: {manifest['region_count']}")
    print(f"Missing signals: {manifest['missing_signal_count']}")
    print(f"SHA-256: {manifest['data_sha256']}")


if __name__ == "__main__":
    main()

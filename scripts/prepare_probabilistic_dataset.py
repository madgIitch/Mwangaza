"""Transform real GEE history into a leakage-safe probabilistic dataset."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path
import sys

from mwangaza.probabilistic.dataset import write_training_dataset
from mwangaza.probabilistic.processing import (
    build_real_training_dataset,
    load_signal_rows,
    threshold_manifest,
    write_threshold_manifest,
)
from mwangaza.probabilistic.progress import EtaProgress


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("data/historical/gee-from-2024/history.jsonl"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("data/historical/gee-baseline-2003-2023/history.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/historical/probabilistic-training.json"),
    )
    parser.add_argument("--min-baseline-years", type=int, default=15)
    parser.add_argument(
        "--reference-end",
        type=date.fromisoformat,
        default=date(2017, 12, 31),
        help="Last date allowed to fit climatology and thresholds.",
    )
    parser.add_argument(
        "--label-start",
        type=date.fromisoformat,
        default=date(2018, 1, 1),
        help="First date allowed in the labeled training history.",
    )
    parser.add_argument(
        "--thresholds-output",
        type=Path,
        default=Path("data/historical/probabilistic-thresholds.json"),
    )
    args = parser.parse_args()

    if not args.baseline.exists():
        parser.error(
            f"baseline not found: {args.baseline}. Run the historical backfill for 2003-2023 first."
        )
    if args.label_start <= args.reference_end:
        parser.error("--label-start must be later than --reference-end")
    recent = load_signal_rows(args.history)
    baseline_raw = load_signal_rows(args.baseline)
    baseline = tuple(
        row
        for row in baseline_raw
        if date.fromisoformat(row.period_end) <= args.reference_end
    )
    labeled_by_key = {
        row.key: row
        for row in (*baseline_raw, *recent)
        if date.fromisoformat(row.period_start) >= args.label_start
    }
    current = tuple(
        sorted(labeled_by_key.values(), key=lambda row: (row.region_id, row.period_start))
    )
    print(f"Reference rows: {len(baseline)}")
    print(f"Labeled history rows: {len(current)}")
    print(f"Reference cutoff: {args.reference_end}")
    print(f"Label start: {args.label_start}")
    dataset = build_real_training_dataset(
        current,
        baseline,
        min_baseline_years=args.min_baseline_years,
        progress=EtaProgress("Data treatment"),
    )
    thresholds = threshold_manifest(
        baseline, min_baseline_years=args.min_baseline_years
    )
    write_training_dataset(dataset, args.output)
    write_threshold_manifest(thresholds, args.thresholds_output)
    targets = Counter(
        f"h{row.horizon_periods}:{row.target}" for row in dataset.rows
    )
    print(f"Output: {args.output}")
    print(f"Dataset hash: {dataset.dataset_hash}")
    print(f"Thresholds: {args.thresholds_output}")
    print(f"Rows: {len(dataset.rows)}")
    print(f"Targets: {dict(sorted(targets.items()))}")
    for horizon in (1, 2, 3):
        classes = {
            row.target
            for row in dataset.rows
            if row.horizon_periods == horizon and row.target is not None
        }
        if classes != {0, 1}:
            print(
                f"WARNING: horizon {horizon} has classes {sorted(classes)}; "
                "training will reject it. Do not weaken thresholds silently.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()

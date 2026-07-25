"""Train probabilistic candidates from the real prepared dataset."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from mwangaza.probabilistic.dataset import load_training_dataset
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.probabilistic.training import (
    TrainingConfig,
    canonical_training_run_json,
    train_risk_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/historical/probabilistic-training.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/probabilistic-training-run.json"),
    )
    parser.add_argument("--initial-periods", type=int, default=36)
    parser.add_argument("--min-train-rows", type=int, default=160)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    dataset = load_training_dataset(args.dataset)
    print(f"Dataset: {len(dataset.rows)} rows")
    print(f"Regions: {len(dataset.regions)}")
    print(f"Dataset hash: {dataset.dataset_hash}")
    run = train_risk_candidates(
        dataset,
        TrainingConfig(
            seed=args.seed,
            initial_train_periods=args.initial_periods,
            min_train_rows=args.min_train_rows,
        ),
        progress=EtaProgress("Model training"),
    )
    _atomic_write(args.output, canonical_training_run_json(run))
    for result in run.results:
        print(
            f"{result.horizon_days} days: status={result.status} "
            f"selected={result.selected_model or 'none'}"
        )
        for candidate in result.candidates:
            score = "n/a" if candidate.brier_score is None else f"{candidate.brier_score:.6f}"
            print(f"  {candidate.name:<24} Brier={score}")
    print(f"Run hash: {run.run_hash}")
    print(f"Output: {args.output}")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()

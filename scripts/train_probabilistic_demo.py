"""Run the Sprint 62 probabilistic trainer against a reproducible demo dataset."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from mwangaza.probabilistic.dataset import HistoricalRiskPeriod, build_training_dataset
from mwangaza.probabilistic.training import TrainingConfig, train_risk_candidates


def _dekad_date(index: int) -> datetime:
    year = 2018 + index // 36
    within_year = index % 36
    month = within_year // 3 + 1
    day = (within_year % 3) * 10 + 1
    return datetime(year, month, day, tzinfo=timezone.utc)


def _build_demo_dataset(periods: int, regions: int):
    observations: list[HistoricalRiskPeriod] = []
    for index in range(periods):
        driver = 1 if ((index * 17 + index // 7) % 11) < 5 else 0
        previous_driver = 1 if (((index - 1) * 17 + (index - 1) // 7) % 11) < 5 else 0
        for region in range(regions):
            observations.append(
                HistoricalRiskPeriod(
                    region_id=f"REGION-{region + 1}",
                    as_of=_dekad_date(index),
                    frequency="dekadal",
                    risk_level="orange" if previous_driver else "yellow",
                    quality_flag="ok",
                    threshold_version="thresholds-demo-v1",
                    source_version="signals-demo-v1",
                    transformation_version="features-demo-v1",
                    score_version="score-demo-v1",
                    geometry_version="geometry-demo-v1",
                    signals={
                        "risk_score": 80.0 if driver else 20.0,
                        "rainfall_anomaly": -20.0 if driver else 5.0,
                        "ndvi_anomaly": -0.3 if driver else 0.1,
                    },
                )
            )
    return build_training_dataset(observations)


def _format_score(score: float | None) -> str:
    return "n/a" if score is None else f"{score:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and compare the Sprint 62 probabilistic candidates."
    )
    parser.add_argument("--periods", type=int, default=48, help="Dekads to generate.")
    parser.add_argument("--regions", type=int, default=3, help="Demo regions.")
    parser.add_argument("--seed", type=int, default=2026, help="Training seed.")
    args = parser.parse_args()

    if args.periods < 1 or args.regions < 1:
        parser.error("--periods and --regions must be positive")

    dataset = _build_demo_dataset(args.periods, args.regions)
    run = train_risk_candidates(
        dataset,
        TrainingConfig(
            seed=args.seed,
            initial_train_periods=36,
            min_train_rows=40,
        ),
    )

    print("Mwangaza probabilistic training demo")
    print(f"Dataset: {len(dataset.rows)} rows, {args.periods} dekads, {args.regions} regions")
    print(f"Dataset hash: {run.dataset_hash}")
    print(f"Run hash: {run.run_hash}")
    print(f"scikit-learn: {run.sklearn_version}")

    for result in run.results:
        print(f"\nHorizon: {result.horizon_days} days ({result.horizon_periods} dekads)")
        print(f"Status: {result.status} ({result.reason})")
        print(f"Selected model: {result.selected_model or 'none'}")
        print(f"Walk-forward folds: {len(result.folds)}")
        for candidate in result.candidates:
            print(
                f"  {candidate.name:<24} "
                f"Brier={_format_score(candidate.brier_score):>8} "
                f"status={candidate.status}"
            )


if __name__ == "__main__":
    main()

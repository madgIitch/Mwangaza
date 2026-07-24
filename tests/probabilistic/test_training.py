from __future__ import annotations

from datetime import datetime, timezone

from mwangaza.probabilistic.dataset import HistoricalRiskPeriod, build_training_dataset
from mwangaza.probabilistic.training import (
    TrainingConfig,
    canonical_training_run_json,
    train_risk_candidates,
)


def _dekad_date(index: int) -> datetime:
    year = 2018 + index // 36
    within_year = index % 36
    month = within_year // 3 + 1
    day = (within_year % 3) * 10 + 1
    return datetime(year, month, day, tzinfo=timezone.utc)


def _dataset(periods: int = 48, regions: int = 3):
    observations = []
    for index in range(periods):
        driver = 1 if ((index * 17 + index // 7) % 11) < 5 else 0
        previous_driver = 1 if (((index - 1) * 17 + (index - 1) // 7) % 11) < 5 else 0
        for region in range(regions + (1 if index >= 40 else 0)):
            observations.append(
                HistoricalRiskPeriod(
                    region_id=f"REGION-{region}",
                    as_of=_dekad_date(index),
                    frequency="dekadal",
                    risk_level="orange" if previous_driver else "yellow",
                    quality_flag="ok",
                    threshold_version="thresholds-v1",
                    source_version="signals-v1",
                    transformation_version="features-v1",
                    score_version="score-v1",
                    geometry_version="geometry-v1",
                    signals={
                        "risk_score": 80.0 if driver else 20.0,
                        "rainfall_anomaly": -20.0 if driver else 5.0,
                        "ndvi_anomaly": -0.3 if driver else 0.1,
                    },
                )
            )
    return build_training_dataset(observations)


def test_walk_forward_is_global_gapped_and_reproducible() -> None:
    dataset = _dataset()
    config = TrainingConfig(initial_train_periods=36, min_train_rows=40)
    first = train_risk_candidates(dataset, config)
    second = train_risk_candidates(dataset, config)

    assert first.run_hash == second.run_hash
    assert canonical_training_run_json(first) == canonical_training_run_json(second)
    for result in first.results:
        assert result.horizon_days in {10, 20, 30}
        assert result.folds
        assert all(fold.gap_periods == result.horizon_periods for fold in result.folds)
        assert all(fold.train_end < fold.test_as_of for fold in result.folds)


def test_candidates_produce_bounded_oof_probabilities_and_manifest() -> None:
    run = train_risk_candidates(
        _dataset(), TrainingConfig(initial_train_periods=36, min_train_rows=40)
    )

    assert run.dataset_hash.startswith("sha256:")
    assert run.sklearn_version
    assert run.threshold_versions == ("thresholds-v1",)
    assert any(result.status == "selected" for result in run.results), [
        (result.horizon_periods, [(item.name, item.brier_score) for item in result.candidates])
        for result in run.results
    ]
    assert any(
        prediction.region_id == "REGION-3"
        for result in run.results
        for candidate in result.candidates
        for prediction in candidate.predictions
    )
    for result in run.results:
        if result.status == "selected":
            assert result.selected_model in {"logistic_regression", "hist_gradient_boosting"}
        assert {candidate.name for candidate in result.candidates} == {
            "persistence",
            "seasonal_climatology",
            "historical_frequency",
            "logistic_regression",
            "hist_gradient_boosting",
        }
        for candidate in result.candidates:
            if candidate.status == "evaluated":
                assert candidate.brier_score is not None
                assert all(0 <= item.probability <= 1 for item in candidate.predictions)


def test_rejects_horizon_when_history_or_classes_are_insufficient() -> None:
    short = train_risk_candidates(
        _dataset(periods=7),
        TrainingConfig(initial_train_periods=6, min_train_rows=12),
    )
    assert all(result.status == "rejected_insufficient_skill" for result in short.results)

    one_class_observations = [
        HistoricalRiskPeriod(
            region_id="REGION-0",
            as_of=_dekad_date(index),
            frequency="dekadal",
            risk_level="yellow",
            quality_flag="ok",
            threshold_version="v1",
            source_version="v1",
            transformation_version="v1",
            score_version="v1",
            geometry_version="v1",
            signals={"risk_score": 20.0},
        )
        for index in range(45)
    ]
    one_class = train_risk_candidates(
        build_training_dataset(one_class_observations),
        TrainingConfig(initial_train_periods=12, min_train_rows=8),
    )
    assert all(
        result.reason in {"no_eligible_folds", "insufficient_periods"}
        for result in one_class.results
    )

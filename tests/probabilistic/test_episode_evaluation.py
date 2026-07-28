from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from mwangaza.probabilistic.episode_evaluation import (
    ActualEpisode,
    EpisodeEvaluationConfig,
    EpisodeEvaluationError,
    EvaluationRow,
    HazardObservation,
    OofEpisodePrediction,
    build_evaluation_rows,
    episode_metrics,
    episode_skill_decision,
    evaluate_candidates,
    group_predicted_episodes,
    load_hazard_observations,
)


def test_only_validated_known_hazard_phases_become_targets(tmp_path: Path) -> None:
    rows = [
        _label("a", "phase_alert", "validated"),
        _label("n", "phase_normal", "validated"),
        _label("u", "phase_unknown", "validated"),
        _label("r", "phase_alarm", "review_required"),
    ]
    path = tmp_path / "independent-labels.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    loaded = load_hazard_observations(path)

    assert [(item.label_id, item.target) for item in loaded] == [("a", 1), ("n", 0)]


def test_alignment_keeps_unknown_out_and_rejects_future_features(tmp_path: Path) -> None:
    feature_path = tmp_path / "adm1-features.jsonl"
    feature_path.write_text(
        json.dumps(_feature("2019-12-31", "2020-01-01T00:00:00Z")) + "\n",
        encoding="utf-8",
    )
    observations = (
        HazardObservation(
            "not-yet-issued",
            "adm1-ke-01",
            "2019-12-01",
            "2019-12-31",
            "2020-01-02T00:00:00Z",
            0,
            "phase_normal",
        ),
        HazardObservation(
            "active",
            "adm1-ke-01",
            "2020-01-01",
            "2020-01-31",
            "2020-01-01T00:00:00Z",
            1,
            "phase_alert",
        ),
    )
    episodes = (
        ActualEpisode(
            "episode-1", "adm1-ke-01", "2020-01-01", "2020-01-31", False, False
        ),
    )

    aligned = build_evaluation_rows(
        feature_path, observations, episodes, horizons_days=(10, 40)
    )

    assert len(aligned) == 1
    assert aligned[0].target_date == "2020-01-10"
    assert aligned[0].target == 1
    assert aligned[0].episode_id == "episode-1"
    assert aligned[0].current_active is None

    unsafe = _feature("2019-12-31", "2020-01-01T00:00:00Z")
    unsafe["signals"]["spi_3m"]["available_at"] = "2020-01-02T00:00:00Z"
    feature_path.write_text(json.dumps(unsafe) + "\n", encoding="utf-8")
    with pytest.raises(EpisodeEvaluationError, match="unavailable at as_of"):
        build_evaluation_rows(feature_path, observations, episodes, horizons_days=(10,))


def test_predicted_episode_gap_32_joins_and_33_splits() -> None:
    first = _prediction("2020-01-01", "2019-12-22")
    second = _prediction("2020-02-02", "2020-01-23")
    third = _prediction("2020-03-06", "2020-02-25")

    grouped = group_predicted_episodes((first, second, third), max_gap_days=32)

    assert len(grouped) == 2
    assert grouped[0].point_count == 2
    assert grouped[1].point_count == 1


def test_episode_metrics_use_one_to_one_matching_and_censor_denominators() -> None:
    truth = ActualEpisode(
        "actual", "adm1-ke-01", "2020-01-01", "2020-01-31", False, False
    )
    positive = _prediction("2020-01-10", "2019-12-31")
    false_alarm = replace(
        _prediction("2020-03-10", "2020-02-29"), actual=0, actual_episode_id=None
    )
    predicted = group_predicted_episodes((positive, false_alarm))

    metrics = episode_metrics((positive, false_alarm), predicted, {"actual": truth})

    assert metrics["event_recall"] == 1.0
    assert metrics["event_precision"] == 0.5
    assert metrics["false_alarm_count"] == 1
    assert metrics["mean_lead_days"] == 1.0
    assert metrics["onset_metric_denominator"] == 1
    assert metrics["recovery_metric_denominator"] == 1

    censored = replace(truth, left_censored=True, right_censored=True)
    censored_metrics = episode_metrics(
        (positive,), group_predicted_episodes((positive,)), {"actual": censored}
    )
    assert censored_metrics["onset_metric_denominator"] == 0
    assert censored_metrics["recovery_metric_denominator"] == 0


def test_skill_gate_requires_brier_f1_false_alarms_and_support() -> None:
    baseline = {
        "brier_score": 0.2,
        "event_f1": 0.5,
        "false_alarm_count": 3,
        "actual_episode_count": 4,
    }
    skilled = {
        "brier_score": 0.1,
        "event_f1": 0.6,
        "false_alarm_count": 3,
        "actual_episode_count": 4,
    }
    assert episode_skill_decision(skilled, baseline) == (
        "episode_skill_eligible",
        "improves_best_baseline",
    )
    assert episode_skill_decision({**skilled, "false_alarm_count": 4}, baseline)[0] == "rejected"
    assert episode_skill_decision({**skilled, "actual_episode_count": 1}, baseline) == (
        "rejected",
        "insufficient_test_episodes",
    )


def test_walk_forward_keeps_cross_year_episode_in_one_fold_and_is_deterministic() -> None:
    episodes = (
        ActualEpisode("cross", "a", "2020-12-01", "2021-01-31", False, False),
        ActualEpisode("b-2020", "b", "2020-01-01", "2020-01-31", False, False),
        ActualEpisode("a-2021", "a", "2021-07-01", "2021-07-31", False, False),
        ActualEpisode("b-2021", "b", "2021-07-01", "2021-07-31", False, False),
    )
    rows = []
    for year in range(2018, 2022):
        for month in range(1, 13):
            for region in ("a", "b"):
                episode_id = _synthetic_episode_id(region, year, month)
                target = int(episode_id is not None)
                rows.append(
                    EvaluationRow(
                        region_id=region,
                        as_of=f"{year:04d}-{month:02d}-05T00:00:00Z",
                        target_date=f"{year:04d}-{month:02d}-15",
                        horizon_days=10,
                        target=target,
                        episode_id=episode_id,
                        current_active=0,
                        features={"region_id": region, "synthetic_signal": float(target)},
                    )
                )
    config = EpisodeEvaluationConfig(
        horizons_days=(10,), first_test_year=2020, min_train_rows=12, min_class_count=2
    )

    first = evaluate_candidates(rows, episodes, config)
    second = evaluate_candidates(rows, episodes, config)

    assert first["run_hash"] == second["run_hash"]
    cross_folds = {
        row["fold"]
        for row in first["predictions"]
        if row["actual_episode_id"] == "cross"
    }
    assert len(cross_folds) == 1
    assert {row["region_id"] for row in first["predictions"]} == {"a", "b"}


def _label(label_id: str, value: str, review_status: str) -> dict[str, object]:
    return {
        "label_id": label_id,
        "label_semantics": "drought_hazard_event",
        "review_status": review_status,
        "adm1_region_id": "adm1-ke-01",
        "normalized_value": value,
        "valid_from": "2020-01-01",
        "valid_to": "2020-01-31",
        "issued_at": "2020-01-01T00:00:00Z",
    }


def _feature(period_end: str, as_of: str) -> dict[str, object]:
    return {
        "region_id": "adm1-ke-01",
        "period_end": period_end,
        "as_of": as_of,
        "signals": {
            "spi_3m": {
                "value": -1.5,
                "age_days": 1,
                "available_at": as_of,
            }
        },
    }


def _prediction(target_date: str, as_of: str) -> OofEpisodePrediction:
    return OofEpisodePrediction(
        candidate="logistic_regression",
        fold=0,
        region_id="adm1-ke-01",
        as_of=as_of,
        target_date=target_date,
        horizon_days=10,
        actual=1,
        actual_episode_id="actual",
        probability=0.9,
    )


def _synthetic_episode_id(region: str, year: int, month: int) -> str | None:
    if region == "a" and ((year, month) in {(2020, 12), (2021, 1)}):
        return "cross"
    if region == "b" and (year, month) == (2020, 1):
        return "b-2020"
    if month == 7 and year == 2021:
        return f"{region}-2021"
    if year < 2020 and month in {3, 9}:
        return f"train-{region}-{year}-{month}"
    return None

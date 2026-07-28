from __future__ import annotations

import json
from pathlib import Path

import pytest

from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.survival import (
    PhaseObservation,
    SurvivalConfig,
    SurvivalEvaluationError,
    SurvivalRow,
    apply_monotonic_probabilities,
    build_survival_rows,
    continuation_skill_decision,
    evaluate_survival,
    refine_survival_episodes,
    risk_set_payload,
    split_survival_rows,
    validate_holdout_unlock,
)


def test_risk_set_contains_only_active_as_of_and_known_recovery_targets(
    tmp_path: Path,
) -> None:
    features = tmp_path / "adm1-features.jsonl"
    features.write_text(
        json.dumps(_feature("2020-01-31", "2020-02-01T00:00:00Z")) + "\n",
        encoding="utf-8",
    )
    observations = (
        _phase("active", "2020-01-01", "2020-03-31", True, "phase_alert"),
        _phase("recovery", "2020-04-01", "2020-04-30", False, "phase_recovery"),
    )
    episodes = (
        ActualEpisode(
            "episode", "adm1-ke-01", "2020-01-01", "2020-03-31", False, False
        ),
    )

    rows = build_survival_rows(features, observations, episodes)

    assert len(rows) == 1
    assert rows[0].elapsed_days == 30
    assert rows[0].targets == {30: 1, 60: 1, 90: 0, 180: 0}
    assert rows[0].target_reasons[90] == "validated_recovery"

    features.write_text(
        json.dumps(_feature("2020-04-10", "2020-04-11T00:00:00Z")) + "\n",
        encoding="utf-8",
    )
    assert build_survival_rows(features, observations, episodes) == ()


def test_recovery_without_validated_inactive_phase_remains_unknown(tmp_path: Path) -> None:
    features = tmp_path / "features.jsonl"
    features.write_text(
        json.dumps(_feature("2020-01-30", "2020-01-31T00:00:00Z")) + "\n",
        encoding="utf-8",
    )
    episode = ActualEpisode(
        "episode", "adm1-ke-01", "2020-01-01", "2020-02-29", False, True
    )
    row = build_survival_rows(
        features,
        (_phase("active", "2020-01-01", "2020-02-29", True, "phase_alarm"),),
        (episode,),
    )[0]
    assert row.targets[30] == 1
    assert row.targets[60] is None
    assert row.target_reasons[60] == "recovery_unobserved"


def test_future_phase_or_signal_is_not_exposed_at_as_of(tmp_path: Path) -> None:
    features = tmp_path / "features.jsonl"
    payload = _feature("2020-01-31", "2020-02-01T00:00:00Z")
    payload["signals"]["spi_3m"]["available_at"] = "2020-02-02T00:00:00Z"
    features.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    observations = (
        _phase(
            "future-phase",
            "2020-01-01",
            "2020-02-29",
            True,
            "phase_alert",
            issued_at="2020-02-02T00:00:00Z",
        ),
    )
    episode = ActualEpisode(
        "episode", "adm1-ke-01", "2020-01-01", "2020-02-29", False, False
    )
    assert build_survival_rows(features, observations, (episode,)) == ()

    observations = (_phase("active", "2020-01-01", "2020-02-29", True, "phase_alert"),)
    with pytest.raises(SurvivalEvaluationError, match="unavailable at as_of"):
        build_survival_rows(features, observations, (episode,))


def test_split_purges_boundary_episodes_and_keeps_sets_disjoint() -> None:
    episodes = (
        _episode("train", "2019-01-01", "2020-12-31"),
        _episode("cross-2021", "2020-12-01", "2021-02-28"),
        _episode("validation", "2021-03-01", "2023-12-31"),
        _episode("cross-2024", "2023-12-01", "2024-02-29"),
        _episode("holdout", "2024-03-01", "2025-01-31"),
    )
    rows = tuple(_row(item.episode_id, item.valid_from, 100) for item in episodes)

    splits = split_survival_rows(rows, episodes)

    assert {row.episode_id for row in splits["train"]} == {"train"}
    assert {row.episode_id for row in splits["validation"]} == {"validation"}
    assert {row.episode_id for row in splits["holdout"]} == {"holdout"}
    assert {row.episode_id for row in splits["purged_boundary"]} == {
        "cross-2021",
        "cross-2024",
    }


def test_explicit_normal_or_unknown_month_splits_survival_episode() -> None:
    parent = _episode("audited", "2020-01-01", "2020-05-31")
    observations = (
        _phase("jan", "2020-01-01", "2020-01-31", True, "phase_alert"),
        _phase("normal", "2020-02-01", "2020-02-29", False, "phase_normal"),
        _phase("mar", "2020-03-01", "2020-03-31", True, "phase_alert"),
        _phase("may", "2020-05-01", "2020-05-31", True, "phase_alarm"),
        _phase("recovery", "2020-06-01", "2020-06-30", False, "phase_recovery"),
    )

    refined = refine_survival_episodes((parent,), observations)

    assert [(item.valid_from, item.valid_to) for item in refined] == [
        ("2020-01-01", "2020-01-31"),
        ("2020-03-01", "2020-03-31"),
        ("2020-05-01", "2020-05-31"),
    ]
    assert all(item.right_censored is False for item in refined)


def test_monotonic_projection_and_skill_gate() -> None:
    assert apply_monotonic_probabilities({30: 0.8, 60: 0.9, 90: 0.4, 180: 0.5}) == {
        30: 0.8,
        60: 0.8,
        90: 0.4,
        180: 0.4,
    }
    baseline = _metrics(0.2, 40.0)
    skilled = _metrics(0.1, 30.0)
    assert continuation_skill_decision(skilled, baseline) == (
        "continuation_skill_eligible",
        "improves_integrated_brier_and_recovery",
    )
    skilled["horizons"][2]["brier_score"] = 0.3
    assert continuation_skill_decision(skilled, baseline)[0] == "rejected"


def test_risk_set_payload_preserves_features_targets_and_input_hashes() -> None:
    row = _row("episode", "2020-01-10", 75)

    payload = risk_set_payload(row, {"labels": "sha256:labels", "features": "sha256:data"})

    assert payload["features"] == row.features
    assert payload["targets"] == row.targets
    assert payload["input_hashes"] == {
        "features": "sha256:data",
        "labels": "sha256:labels",
    }


def test_validation_run_is_deterministic_and_reports_ablation() -> None:
    episodes = []
    rows = []
    remaining_values = (15, 45, 75, 120, 210)
    for year, prefix in ((2018, "train-a"), (2019, "train-b"), (2020, "train-c")):
        for index, remaining in enumerate(remaining_values):
            episode = _episode(
                f"{prefix}-{index}", f"{year}-01-01", f"{year}-12-31"
            )
            episodes.append(episode)
            rows.append(_row(episode.episode_id, f"{year}-01-10", remaining))
    for year, prefix in ((2021, "valid-a"), (2022, "valid-b"), (2023, "valid-c")):
        for index, remaining in enumerate(remaining_values):
            episode = _episode(
                f"{prefix}-{index}", f"{year}-01-01", f"{year}-12-31"
            )
            episodes.append(episode)
            rows.append(_row(episode.episode_id, f"{year}-01-10", remaining))
    config = SurvivalConfig(min_train_rows=10, min_class_count=2)

    first = evaluate_survival(rows, episodes, config=config)
    second = evaluate_survival(rows, episodes, config=config)

    assert first["run_hash"] == second["run_hash"]
    assert first["test_episode_count"] == 15
    assert len(first["ablation"]) == 5
    predictions = first["predictions"]
    for candidate in {item["candidate"] for item in predictions}:
        candidate_rows = [item for item in predictions if item["candidate"] == candidate]
        for sample_id in {item["sample_id"] for item in candidate_rows}:
            values = [
                item["probability"]
                for item in sorted(
                    (item for item in candidate_rows if item["sample_id"] == sample_id),
                    key=lambda item: item["horizon_days"],
                )
            ]
            assert values == sorted(values, reverse=True)


def test_holdout_requires_matching_frozen_hash_and_opens_once(tmp_path: Path) -> None:
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "manifest.json").write_text(
        json.dumps({"run_hash": "sha256:frozen"}), encoding="utf-8"
    )
    with pytest.raises(SurvivalEvaluationError, match="requires"):
        validate_holdout_unlock(tmp_path, None)
    with pytest.raises(SurvivalEvaluationError, match="does not match"):
        validate_holdout_unlock(tmp_path, "sha256:other")
    assert validate_holdout_unlock(tmp_path, "sha256:frozen") == "sha256:frozen"
    holdout = tmp_path / "holdout"
    holdout.mkdir()
    (holdout / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SurvivalEvaluationError, match="already been opened"):
        validate_holdout_unlock(tmp_path, "sha256:frozen")


def _phase(
    label_id: str,
    valid_from: str,
    valid_to: str,
    active: bool,
    phase: str,
    *,
    issued_at: str | None = None,
) -> PhaseObservation:
    return PhaseObservation(
        label_id,
        "adm1-ke-01",
        valid_from,
        valid_to,
        issued_at or valid_from + "T00:00:00Z",
        active,
        phase,
        "stable",
    )


def _feature(period_end: str, as_of: str) -> dict[str, object]:
    return {
        "region_id": "adm1-ke-01",
        "period_end": period_end,
        "as_of": as_of,
        "signals": {
            "spi_3m": {"value": -1.2, "age_days": 1, "available_at": as_of},
            "ndvi": {"value": 0.3, "age_days": 4, "available_at": as_of},
            "soil_moisture_rootzone": {
                "value": 0.2,
                "age_days": 20,
                "available_at": as_of,
            },
            "evapotranspiration_rate": {
                "value": 0.1,
                "age_days": 20,
                "available_at": as_of,
            },
        },
    }


def _episode(episode_id: str, start: str, end: str) -> ActualEpisode:
    return ActualEpisode(episode_id, "adm1-ke-01", start, end, False, False)


def _row(episode_id: str, period_end: str, remaining: int) -> SurvivalRow:
    targets = {horizon: int(remaining >= horizon) for horizon in (30, 60, 90, 180)}
    return SurvivalRow(
        sample_id=f"sample-{episode_id}",
        episode_id=episode_id,
        region_id="adm1-ke-01",
        as_of=period_end + "T00:00:00Z",
        period_end=period_end,
        elapsed_days=20,
        left_censored=False,
        current_phase="phase_alert",
        current_trend="stable",
        features={
            "region_id": "adm1-ke-01",
            "spi_3m": float(remaining),
            "ndvi": float(remaining),
            "soil_moisture_rootzone": float(remaining),
            "evapotranspiration_rate": float(remaining),
            "season_sin": 0.1,
        },
        targets=targets,
        target_reasons={horizon: "fixture" for horizon in targets},
    )


def _metrics(brier: float, recovery_error: float) -> dict[str, object]:
    return {
        "integrated_brier": brier,
        "mean_absolute_recovery_error_days": recovery_error,
        "test_episode_count": 10,
        "horizons": [
            {"horizon_days": horizon, "brier_score": brier}
            for horizon in (30, 60, 90, 180)
        ],
    }

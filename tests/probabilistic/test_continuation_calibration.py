from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from mwangaza.probabilistic.continuation_calibration import (
    ContinuationCalibrationError,
    HybridGateConfig,
    assert_pre_holdout,
    build_global_routes,
    build_nested_calibration_folds,
    build_phase_baselines,
    evaluate_hybrid_continuation,
    fit_platt_calibrator,
    hybrid_ml_gate,
    load_continuation_model_bundle,
)
from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.survival import SurvivalRow


def test_nested_folds_keep_base_calibration_and_evaluation_episodes_disjoint() -> None:
    episodes, rows = _history()

    folds = build_nested_calibration_folds(rows, episodes, _config())

    assert [fold.evaluation_year for fold in folds] == [2021, 2022, 2023]
    first = folds[0]
    assert all("2020" not in value for value in first.base_episode_ids)
    assert all("2020" in value for value in first.calibration_episode_ids)
    assert all("2021" in value for value in first.evaluation_episode_ids)
    assert not (
        set(first.base_episode_ids)
        & set(first.calibration_episode_ids)
        & set(first.evaluation_episode_ids)
    )


def test_holdout_sentinel_rejects_rows_or_episodes_from_2024() -> None:
    episode = _episode("holdout", 2024, 0)
    row = _row(episode, 1, 0)

    with pytest.raises(ContinuationCalibrationError, match="holdout row forbidden"):
        assert_pre_holdout((row,), ())
    with pytest.raises(ContinuationCalibrationError, match="holdout episode forbidden"):
        assert_pre_holdout((), (episode,))


def test_platt_calibrator_produces_ordered_bounded_probabilities() -> None:
    calibrator = fit_platt_calibrator((0.1, 0.2, 0.8, 0.9), (0, 0, 1, 1))

    probabilities = calibrator.predict((0.01, 0.25, 0.75, 0.99))

    assert probabilities == sorted(probabilities)
    assert all(0 < value < 1 for value in probabilities)


def test_gate_requires_skill_support_calibration_and_valid_hashes() -> None:
    calibrated = _metrics(brier=0.08, bss=0.2, ece=0.05)
    raw = _metrics(brier=0.09, bss=0.1, ece=0.08)
    hashes = {"features": "sha256:" + "a" * 64}
    config = _config()

    assert hybrid_ml_gate(calibrated, raw, hashes, config) == (
        "ml_experimental",
        [],
    )
    calibrated["brier_skill_score"] = 0.0
    status, reasons = hybrid_ml_gate(calibrated, raw, hashes, config)
    assert status == "baseline"
    assert "non_positive_brier_skill" in reasons


def test_phase_baselines_are_monotonic_and_keep_support() -> None:
    episodes, rows = _history()

    baselines = build_phase_baselines(rows, _config())

    probabilities = [
        baselines[str(horizon)]["phase_alert"]["probability"]
        for horizon in (30, 60, 90, 180)
    ]
    assert probabilities == sorted(probabilities, reverse=True)
    assert baselines["30"]["phase_alert"]["known_count"] == len(rows)
    assert baselines["30"]["phase_alert"]["eligible"] is True


def test_global_route_is_unavailable_when_no_phase_bucket_has_support() -> None:
    config = _config()
    routes = build_global_routes(
        "baseline",
        ("non_positive_brier_skill",),
        _metrics(brier=0.2, bss=-0.1, ece=0.1),
        {
            str(horizon): {
                "phase_alert": {
                    "probability": 0.5,
                    "known_count": 1,
                    "episode_count": 1,
                    "eligible": False,
                }
            }
            for horizon in (30, 60, 90, 180)
        },
        {"features": "sha256:" + "a" * 64},
        config,
    )

    assert all(route["status"] == "unavailable" for route in routes)


def test_corrupt_or_mismatched_model_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"not a joblib artifact")
    digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()

    with pytest.raises(ContinuationCalibrationError, match="hash mismatch"):
        load_continuation_model_bundle(artifact, "sha256:" + "0" * 64)
    with pytest.raises(ContinuationCalibrationError, match="corrupt"):
        load_continuation_model_bundle(artifact, digest)


def test_hybrid_evaluation_is_deterministic_and_never_uses_holdout() -> None:
    episodes, rows = _history()
    hashes = {
        "features": "sha256:" + "a" * 64,
        "labels": "sha256:" + "b" * 64,
    }

    first = evaluate_hybrid_continuation(
        rows, episodes, input_hashes=hashes, config=_config()
    )
    second = evaluate_hybrid_continuation(
        rows, episodes, input_hashes=hashes, config=_config()
    )

    assert first["run_hash"] == second["run_hash"]
    assert first["holdout_policy"]["used_for_fit_calibration_or_gate"] is False
    assert {route["horizon_days"] for route in first["global_routes"]} == {
        30,
        60,
        90,
        180,
    }
    assert all(
        route["estimator_kind"] != "ml"
        for route in first["global_routes"]
        if route["horizon_days"] != 30
    )


def _history() -> tuple[tuple[ActualEpisode, ...], tuple[SurvivalRow, ...]]:
    episodes = []
    rows = []
    for year in range(2018, 2024):
        for target in (0, 1):
            episode = _episode(f"episode-{year}-{target}", year, target)
            episodes.append(episode)
            for index in range(2):
                rows.append(_row(episode, target, index))
    return tuple(episodes), tuple(rows)


def _episode(episode_id: str, year: int, offset: int) -> ActualEpisode:
    month = 1 + offset * 3
    return ActualEpisode(
        episode_id=episode_id,
        region_id="adm1-ke-01",
        valid_from=date(year, month, 1).isoformat(),
        valid_to=date(year, month + 1, 28).isoformat(),
        left_censored=False,
        right_censored=False,
    )


def _row(episode: ActualEpisode, target: int, index: int) -> SurvivalRow:
    period = date.fromisoformat(episode.valid_from).replace(day=10 + index)
    targets = {
        30: target,
        60: target,
        90: target,
        180: target,
    }
    return SurvivalRow(
        sample_id=f"sample-{episode.episode_id}-{index}",
        episode_id=episode.episode_id,
        region_id=episode.region_id,
        as_of=period.isoformat() + "T00:00:00Z",
        period_end=period.isoformat(),
        elapsed_days=9 + index,
        left_censored=False,
        current_phase="phase_alert",
        current_trend="stable",
        features={
            "region_id": episode.region_id,
            "current_phase": "phase_alert",
            "elapsed_days": float(index),
            "spi_3m": float(target * 2 - 1),
            "soil_moisture_rootzone": float(target),
        },
        targets=targets,
        target_reasons={horizon: "fixture" for horizon in targets},
    )


def _config() -> HybridGateConfig:
    return HybridGateConfig(
        min_known_targets=2,
        min_positive_targets=1,
        min_negative_targets=1,
        min_evaluation_episodes=1,
        max_ece=1.0,
        min_phase_targets=1,
        min_phase_episodes=1,
    )


def _metrics(*, brier: float, bss: float, ece: float) -> dict[str, object]:
    return {
        "known_count": 10,
        "positive_count": 5,
        "negative_count": 5,
        "episode_count": 5,
        "brier_score": brier,
        "brier_skill_score": bss,
        "ece": ece,
    }

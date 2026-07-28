from __future__ import annotations

from collections import defaultdict
from datetime import date

import pytest

from mwangaza.probabilistic.continuation_calibration import (
    ContinuationCalibrationError,
)
from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.ml_sanity_audit import (
    AuditConfig,
    HgbParameters,
    MlSanityAuditError,
    audit_ml_sanity,
    clustered_episode_bootstrap,
    episode_equal_weights,
    fit_hazard,
    fit_hgb,
    fit_weighted_platt,
    missing_indicator_count,
    predict_hazard_continuation,
    skill_verdict,
    temporal_oof_predictions,
)
from mwangaza.probabilistic.survival import SurvivalRow


def test_episode_weights_give_every_episode_total_weight_one() -> None:
    episodes, rows = _history()
    del episodes
    totals: dict[str, float] = defaultdict(float)

    for row, weight in zip(rows, episode_equal_weights(rows), strict=True):
        totals[row.episode_id] += weight

    assert totals
    assert all(total == pytest.approx(1.0) for total in totals.values())


def test_hgb_adds_missing_indicators_and_hazard_outputs_continuation() -> None:
    _, rows = _history()
    config = _config()
    parameters = _parameters()

    hgb = fit_hgb(rows[:12], parameters, config)
    hazard = fit_hazard(rows[:12], 1.0, config)

    assert missing_indicator_count(hgb) >= 1
    assert missing_indicator_count(hazard) >= 1
    probabilities = predict_hazard_continuation(hazard, rows[12:16])
    assert probabilities
    assert all(0 <= value <= 1 for value in probabilities)


def test_temporal_oof_never_predicts_with_future_episode() -> None:
    episodes, rows = _history()

    predictions = temporal_oof_predictions(
        rows,
        episodes,
        _parameters(),
        (2018, 2019),
        _config(),
        estimator_kind="hgb",
    )

    assert {item["year"] for item in predictions} == {2018, 2019}
    assert all(str(item["year"]) in item["episode_id"] for item in predictions)


def test_weighted_platt_uses_both_classes_and_preserves_order() -> None:
    calibrator = fit_weighted_platt(
        (0.1, 0.2, 0.8, 0.9),
        (0, 0, 1, 1),
        (0.5, 0.5, 0.5, 0.5),
        seed=2026,
    )

    values = calibrator.predict((0.05, 0.5, 0.95))

    assert values == sorted(values)
    with pytest.raises(MlSanityAuditError, match="both classes"):
        fit_weighted_platt((0.1, 0.2), (0, 0), (1.0, 1.0), seed=2026)


def test_cluster_bootstrap_resamples_episode_means_and_verdict_uses_ci() -> None:
    rows = [
        {
            "episode_id": episode,
            "actual": actual,
            "baseline": 0.7,
            "candidate": 0.9 if actual else 0.1,
        }
        for episode, actual, count in (("a", 1, 5), ("b", 0, 1), ("c", 1, 2))
        for _ in range(count)
    ]

    bootstrap = clustered_episode_bootstrap(
        rows,
        candidate_field="candidate",
        baseline_field="baseline",
        iterations=200,
        confidence_level=0.95,
        seed=7,
    )
    metrics = {
        "episode_weighted_brier": 0.05,
        "baseline_episode_weighted_brier": 0.2,
        "episode_weighted_ece": 0.1,
    }

    assert bootstrap["episode_count"] == 3
    assert bootstrap["upper_95"] < 0
    assert skill_verdict(metrics, bootstrap, 2, _config()) == "robust_skill"


def test_complete_audit_is_deterministic_and_rejects_2024() -> None:
    episodes, rows = _history()
    hashes = {"features": "sha256:" + "a" * 64}

    first = audit_ml_sanity(
        rows,
        episodes,
        hgb_grid=(_parameters(),),
        input_hashes=hashes,
        config=_config(),
    )
    second = audit_ml_sanity(
        rows,
        episodes,
        hgb_grid=(_parameters(),),
        input_hashes=hashes,
        config=_config(),
    )

    assert first["run_hash"] == second["run_hash"]
    assert first["horizon_days"] == 30
    assert first["holdout_rows_used"] == 0
    future_episode = _episode("episode-2024-1", 2024, 1)
    future_row = _row(future_episode, 1, 0)
    with pytest.raises(ContinuationCalibrationError, match="holdout"):
        audit_ml_sanity(
            (*rows, future_row),
            (*episodes, future_episode),
            hgb_grid=(_parameters(),),
            input_hashes=hashes,
            config=_config(),
        )


def _history() -> tuple[tuple[ActualEpisode, ...], tuple[SurvivalRow, ...]]:
    episodes = []
    rows = []
    for year in range(2016, 2024):
        for target in (0, 1):
            episode = _episode(f"episode-{year}-{target}", year, target)
            episodes.append(episode)
            count = 1 if target else 3
            for index in range(count):
                rows.append(_row(episode, target, index))
    return tuple(episodes), tuple(rows)


def _episode(episode_id: str, year: int, target: int) -> ActualEpisode:
    month = 1 if target else 4
    return ActualEpisode(
        episode_id,
        "adm1-ke-01",
        date(year, month, 1).isoformat(),
        date(year, month + 1, 28).isoformat(),
        False,
        False,
    )


def _row(episode: ActualEpisode, target: int, index: int) -> SurvivalRow:
    period = date.fromisoformat(episode.valid_from).replace(day=10 + index)
    targets = {30: target, 60: target, 90: target, 180: target}
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
            "soil_moisture_rootzone": None if index == 0 else float(target),
        },
        targets=targets,
        target_reasons={horizon: "fixture" for horizon in targets},
    )


def _config() -> AuditConfig:
    return AuditConfig(bootstrap_iterations=100, max_ece=1.0)


def _parameters() -> HgbParameters:
    return HgbParameters(
        max_leaf_nodes=3,
        learning_rate=0.1,
        max_iter=20,
        min_samples_leaf=1,
    )

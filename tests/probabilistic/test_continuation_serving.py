from __future__ import annotations

from datetime import date
from pathlib import Path

import joblib
import pytest

from mwangaza.probabilistic.continuation_serving import (
    AuditEvidence,
    ContinuationServingError,
    ServingConfig,
    freeze_hazard_bundle,
    hazard_drivers,
    load_hazard_bundle,
    materialize_probability_snapshot,
)
from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.survival import PhaseObservation, SurvivalRow

HASH = "sha256:" + "a" * 64


def test_freeze_hazard_is_deterministic_and_excludes_post_2023_fit() -> None:
    rows, episodes = _history()
    future_episode = _episode("future", 2025, "adm1-ke-43")
    future_row = _row(future_episode, 1, 0, period="2025-03-01")

    first = freeze_hazard_bundle(
        (*rows, future_row),
        (*episodes, future_episode),
        evidence=_evidence(),
        input_hashes={"features": HASH},
    )
    second = freeze_hazard_bundle(
        rows,
        episodes,
        evidence=_evidence(),
        input_hashes={"features": HASH},
    )

    assert first.run_hash == second.run_hash
    assert first.trained_through == "2023-12-31"
    assert sum(first.training_region_rows.values()) == len(rows)
    assert "future" not in first.training_region_rows


def test_materialization_keeps_dual_30_day_and_baseline_only_long_horizons() -> None:
    rows, episodes = _history()
    bundle = freeze_hazard_bundle(
        rows,
        episodes,
        evidence=_evidence(),
        input_hashes={"features": HASH},
    )
    current = _row(
        _episode("current", 2026, "adm1-ke-43"),
        None,
        1,
        period="2026-04-01",
    )
    inactive = _observation("adm1-ke-01", active=False, phase="phase_normal")
    snapshot = materialize_probability_snapshot(
        bundle,
        (*rows, current),
        (_observation("adm1-ke-43"), inactive),
        _routing(),
        bundle_sha256=HASH,
        routing_sha256="sha256:" + "b" * 64,
        generated_at="2026-07-28T00:00:00Z",
    )

    active = [item for item in snapshot["items"] if item["region_id"] == "adm1-ke-43"]
    thirty = next(item for item in active if item["horizon_days"] == 30)
    sixty = next(item for item in active if item["horizon_days"] == 60)
    inactive_item = next(
        item
        for item in snapshot["items"]
        if item["region_id"] == "adm1-ke-01" and item["horizon_days"] == 30
    )

    assert [item["kind"] for item in thirty["estimates"]] == [
        "experimental_ml_prediction",
        "historical_reference",
    ]
    assert [item["kind"] for item in sixty["estimates"]] == ["historical_reference"]
    assert thirty["estimates"][0]["validation"]["status"] == "inconclusive"
    assert thirty["estimates"][0]["operational_use"] is False
    assert inactive_item["status"] == "not_applicable"
    assert inactive_item["estimates"] == []


def test_region_without_training_support_blocks_only_ml() -> None:
    rows, episodes = _history()
    bundle = freeze_hazard_bundle(
        rows,
        episodes,
        evidence=_evidence(),
        input_hashes={"features": HASH},
    )
    current = _row(
        _episode("current", 2026, "adm1-ke-99"),
        None,
        1,
        period="2026-04-01",
        region_id="adm1-ke-99",
    )
    snapshot = materialize_probability_snapshot(
        bundle,
        (*rows, current),
        (_observation("adm1-ke-99"),),
        _routing(),
        bundle_sha256=HASH,
        routing_sha256="sha256:" + "b" * 64,
        generated_at="2026-07-28T00:00:00Z",
    )
    item = next(value for value in snapshot["items"] if value["horizon_days"] == 30)
    ml, baseline = item["estimates"]

    assert ml["status"] == "unavailable"
    assert "region_training_support_insufficient" in ml["reason_codes"]
    assert baseline["status"] == "available"
    assert item["status"] == "available"


def test_bundle_loader_verifies_hash_and_drivers_are_non_causal(tmp_path: Path) -> None:
    rows, episodes = _history()
    bundle = freeze_hazard_bundle(
        rows,
        episodes,
        evidence=_evidence(),
        input_hashes={"features": HASH},
    )
    path = tmp_path / "bundle.joblib"
    joblib.dump(bundle, path)
    digest = "sha256:" + __import__("hashlib").sha256(path.read_bytes()).hexdigest()

    loaded = load_hazard_bundle(path, digest)
    drivers = hazard_drivers(loaded, rows[0])

    assert 1 <= len(drivers) <= 3
    assert all(item["causal"] is False for item in drivers)
    with pytest.raises(ContinuationServingError, match="hash mismatch"):
        load_hazard_bundle(path, HASH)


def test_serving_config_cannot_relabel_or_retune_hazard() -> None:
    with pytest.raises(ContinuationServingError, match="frozen"):
        ServingConfig(c=1.0)
    payload = _evidence().__dict__ | {"validation_status": "robust_skill"}
    with pytest.raises(ContinuationServingError, match="inconclusive"):
        AuditEvidence(**payload)


def _history() -> tuple[tuple[SurvivalRow, ...], tuple[ActualEpisode, ...]]:
    rows = []
    episodes = []
    for year in range(2016, 2024):
        for target in (0, 1):
            episode = _episode(f"episode-{year}-{target}", year, "adm1-ke-43")
            episodes.append(episode)
            rows.append(_row(episode, target, target, period=f"{year}-03-01"))
    return tuple(rows), tuple(episodes)


def _episode(identifier: str, year: int, region_id: str) -> ActualEpisode:
    return ActualEpisode(
        episode_id=identifier,
        region_id=region_id,
        valid_from=date(year, 1, 1).isoformat(),
        valid_to=date(year, 6, 30).isoformat(),
        left_censored=False,
        right_censored=False,
    )


def _row(
    episode: ActualEpisode,
    target: int | None,
    index: int,
    *,
    period: str,
    region_id: str | None = None,
) -> SurvivalRow:
    resolved_region = region_id or episode.region_id
    return SurvivalRow(
        sample_id=f"sample-{episode.episode_id}-{index}",
        episode_id=episode.episode_id,
        region_id=resolved_region,
        as_of=f"{period}T00:00:00Z",
        period_end=period,
        elapsed_days=60 + index * 10,
        left_censored=False,
        current_phase="phase_alert",
        current_trend="stable",
        features={
            "region_id": resolved_region,
            "current_phase": "phase_alert",
            "rainfall_mm": 10.0 + index,
            "ndvi": None if index == 0 else 0.3,
        },
        targets={30: target, 60: target, 90: target, 180: target},
        target_reasons={30: "known", 60: "known", 90: "known", 180: "known"},
    )


def _observation(
    region_id: str,
    *,
    active: bool = True,
    phase: str = "phase_alert",
) -> PhaseObservation:
    return PhaseObservation(
        label_id=f"label-{region_id}",
        region_id=region_id,
        valid_from="2026-01-01",
        valid_to="2026-04-30",
        issued_at="2026-01-01T00:00:00Z",
        active=active,
        phase=phase,
        trend="stable",
    )


def _evidence() -> AuditEvidence:
    return AuditEvidence(
        audit_run_hash="sha256:2c2173803f14d7fa77e2d7b64d2742b4817a610ed8d57d4e22c396db2609d666",
        routing_run_hash="sha256:5981338901de379c9943fd2f30b826d0ede687eccff5489657210476e4e74d39",
        validation_status="inconclusive",
        episode_weighted_brier=0.20310233811144818,
        episode_weighted_brier_skill_score=0.15860666146248892,
        episode_weighted_ece=0.1086913943939178,
        bootstrap_delta_brier_lower_95=-0.08394137092155586,
        bootstrap_delta_brier_upper_95=0.002148684985913163,
        improved_outer_folds=2,
        outer_fold_count=3,
    )


def _routing() -> dict[str, object]:
    phase = {
        "eligible": True,
        "episode_count": 20,
        "known_count": 100,
        "probability": 0.7,
    }
    return {
        "run_hash": "sha256:5981338901de379c9943fd2f30b826d0ede687eccff5489657210476e4e74d39",
        "phase_baselines": {
            str(horizon): {"phase_alert": dict(phase)} for horizon in (30, 60, 90, 180)
        },
    }

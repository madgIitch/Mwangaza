from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from mwangaza.probabilistic.dataset import (
    DatasetValidationError,
    HistoricalRiskPeriod,
    build_training_dataset,
    canonical_dataset_json,
    write_training_dataset,
)


def _period(
    month: int,
    *,
    region: str = "KEN-MARSABIT",
    level: str = "yellow",
    quality: str = "ok",
    score: float = 30.0,
) -> HistoricalRiskPeriod:
    return HistoricalRiskPeriod(
        region_id=region,
        as_of=datetime(2025, month, 1, tzinfo=timezone.utc),
        frequency="monthly",
        risk_level=level,
        quality_flag=quality,
        threshold_version="prototype-thresholds-v1",
        source_version="materialized-signals-v1",
        transformation_version="anomalies-v1",
        score_version="composite-v1",
        geometry_version="igad-admin-v1",
        signals={
            "ndvi": 0.5 - month / 100,
            "ndvi_anomaly": -month / 100,
            "rainfall_anomaly": -float(month),
            "risk_score": score,
            "quality_score": 90.0,
            "spatial_coverage": 0.9,
            "temporal_coverage": 1.0,
        },
    )


def _dekad(
    day: int, *, level: str = "yellow", ndvi_observed_day: int | None = None
) -> HistoricalRiskPeriod:
    as_of = datetime(2025, 1, day, tzinfo=timezone.utc)
    observed = (
        datetime(2025, 1, ndvi_observed_day, tzinfo=timezone.utc) if ndvi_observed_day else as_of
    )
    return HistoricalRiskPeriod(
        region_id="KEN-MARSABIT",
        as_of=as_of,
        frequency="dekadal",
        risk_level=level,
        quality_flag="ok",
        threshold_version="v1",
        source_version="v1",
        transformation_version="v1",
        score_version="v1",
        geometry_version="v1",
        signals={"ndvi": 0.4, "rainfall_anomaly": -2.0, "risk_score": 40.0},
        signal_observed_at={
            "ndvi": observed,
            "rainfall_anomaly": as_of,
            "risk_score": as_of,
        },
    )


def test_builds_three_horizons_features_targets_lineage_and_summary() -> None:
    observations = [
        _period(month, level="orange" if month >= 5 else "yellow", score=20 + month * 5)
        for month in range(1, 8)
    ]
    dataset = build_training_dataset(reversed(observations))
    row = next(
        item
        for item in dataset.rows
        if item.as_of.startswith("2025-04") and item.horizon_periods == 1
    )

    assert row.target == 1
    assert row.target_reason == "conclusive"
    assert row.features["risk_score_t"] == 40
    assert row.features["risk_score_lag_3"] == 25
    assert row.features["risk_score_rolling_mean_3"] == 35
    assert row.features["risk_score_slope_3"] == 5
    assert row.features["risk_deterioration_consecutive"] == 3
    assert row.features["rainfall_deficit_rolling_sum_3"] == 9
    assert row.lineage["threshold_version"] == "prototype-thresholds-v1"
    assert row.lineage["target_threshold_version"] == "prototype-thresholds-v1"
    assert dataset.summary["row_count"] == 21
    assert dataset.dataset_hash.startswith("sha256:")


def test_future_sentinel_cannot_change_features_at_as_of() -> None:
    base = [_period(month, score=10 + month) for month in range(1, 7)]
    sentinel = replace(
        _period(7, level="red", score=999_999),
        signals={"risk_score": 999_999.0, "rainfall_anomaly": 999_999.0},
    )
    without = build_training_dataset(base)
    with_future = build_training_dataset([*base, sentinel])
    key = ("2025-06-01T00:00:00Z", 1)
    first = next(row for row in without.rows if (row.as_of, row.horizon_periods) == key)
    second = next(row for row in with_future.rows if (row.as_of, row.horizon_periods) == key)

    assert first.features == second.features
    assert second.target == 1
    assert 999_999.0 not in second.features.values()


def test_gap_does_not_skip_to_older_observation_or_invent_target() -> None:
    dataset = build_training_dataset([_period(1), _period(3), _period(4)])
    march = next(
        row for row in dataset.rows if row.as_of.startswith("2025-03") and row.horizon_periods == 1
    )
    january = next(
        row for row in dataset.rows if row.as_of.startswith("2025-01") and row.horizon_periods == 1
    )

    assert march.features["risk_score_lag_1"] is None
    assert "history_not_contiguous" in march.feature_reasons
    assert january.target is None
    assert january.target_reason == "future_period_missing"


@pytest.mark.parametrize(
    "level,quality,target,reason",
    [
        ("green", "ok", 0, "conclusive"),
        ("yellow", "ok", 0, "conclusive"),
        ("orange", "ok", 1, "conclusive"),
        ("red", "ok", 1, "conclusive"),
        ("unknown", "ok", None, "future_level_unknown"),
        ("red", "invalid", None, "future_quality_blocked"),
    ],
)
def test_target_semantics(level: str, quality: str, target: int | None, reason: str) -> None:
    dataset = build_training_dataset([_period(1), _period(2, level=level, quality=quality)])
    row = next(
        item
        for item in dataset.rows
        if item.as_of.startswith("2025-01") and item.horizon_periods == 1
    )
    assert (row.target, row.target_reason) == (target, reason)


def test_hash_and_serialization_are_stable_for_input_order(tmp_path) -> None:
    items = [_period(month) for month in range(1, 5)] + [
        _period(month, region="SOM-BAY") for month in range(1, 5)
    ]
    first = build_training_dataset(items)
    second = build_training_dataset(reversed(items))

    assert first.dataset_hash == second.dataset_hash
    assert canonical_dataset_json(first) == canonical_dataset_json(second)
    output = write_training_dataset(first, tmp_path / "dataset.json")
    assert json.loads(output.read_text(encoding="utf-8"))["dataset_hash"] == first.dataset_hash
    assert not list(tmp_path.glob("*.tmp"))


def test_rejects_duplicates_mixed_frequency_non_utc_and_non_finite() -> None:
    item = _period(1)
    with pytest.raises(DatasetValidationError, match="duplicate"):
        build_training_dataset([item, item])
    with pytest.raises(DatasetValidationError, match="one frequency"):
        build_training_dataset([item, replace(_period(2), frequency="dekadal")])
    with pytest.raises(DatasetValidationError, match="UTC"):
        replace(item, as_of=datetime(2025, 1, 1))
    with pytest.raises(DatasetValidationError, match="finite"):
        replace(item, signals={"risk_score": float("nan")})


def test_dekadal_rows_expose_10_20_30_day_horizons_and_signal_age() -> None:
    dataset = build_training_dataset(
        [
            _dekad(1),
            _dekad(11, ndvi_observed_day=5),
            _dekad(21, level="orange", ndvi_observed_day=17),
        ]
    )
    rows = [row for row in dataset.rows if row.as_of.startswith("2025-01-11")]

    assert [row.horizon_days for row in rows] == [10, 20, 30]
    assert rows[0].features["ndvi_age_days"] == 6
    assert rows[0].target == 1


def test_signal_observation_date_cannot_leak_from_future() -> None:
    with pytest.raises(DatasetValidationError, match="cannot be after as_of"):
        replace(
            _dekad(11),
            signal_observed_at={"ndvi": datetime(2025, 1, 12, tzinfo=timezone.utc)},
        )

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone

from mwangaza.probabilistic.backfill import HistoricalSignalRow
from mwangaza.probabilistic.processing import (
    build_real_training_dataset,
    threshold_manifest,
)


def _row(
    region: str,
    year: int,
    month: int,
    day: int,
    *,
    rainfall: float,
    ndvi: float,
    lst: float,
) -> HistoricalSignalRow:
    end_day = 10 if day == 1 else 20 if day == 11 else monthrange(year, month)[1]
    start = date(year, month, day)
    end = date(year, month, end_day)
    as_of = datetime(end.year, end.month, end.day, tzinfo=timezone.utc).isoformat()
    return HistoricalSignalRow(
        region_id=region,
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        as_of=as_of,
        rainfall_mm=rainfall,
        rainfall_available_days=(end - start).days + 1,
        rainfall_observed_at=as_of,
        ndvi=ndvi,
        ndvi_observed_at=start.isoformat(),
        ndvi_age_days=(end - start).days,
        lst_c=lst,
        lst_observed_at=start.isoformat(),
        lst_age_days=(end - start).days,
        quality_flag="ok",
        missing_reasons=(),
        source_mode="live",
        geometry_version="v1",
    )


def test_real_processing_builds_versioned_labels_and_targets() -> None:
    baseline = tuple(
        _row(
            "ken",
            year,
            1,
            day,
            rainfall=50.0 + (year % 5),
            ndvi=0.5 + (year % 5) * 0.01,
            lst=30.0 + (year % 5),
        )
        for year in range(2003, 2024)
        for day in (1, 11, 21)
    )
    current = tuple(
        _row(
            "ken",
            2024,
            month,
            day,
            rainfall=10.0 if index >= 3 else 52.0,
            ndvi=0.2 if index >= 3 else 0.52,
            lst=40.0 if index >= 3 else 32.0,
        )
        for index, (month, day) in enumerate(
            ((1, 1), (1, 11), (1, 21), (2, 1), (2, 11), (2, 21))
        )
    )
    # Repeat the January climatology for February to keep the fixture compact.
    baseline += tuple(
        _row(
            "ken",
            year,
            2,
            day,
            rainfall=50.0 + (year % 5),
            ndvi=0.5 + (year % 5) * 0.01,
            lst=30.0 + (year % 5),
        )
        for year in range(2003, 2024)
        for day in (1, 11, 21)
    )

    dataset = build_real_training_dataset(current, baseline)

    assert dataset.frequency == "dekadal"
    assert dataset.summary["observation_count"] == 6
    assert any(row.features["risk_score_t"] == 100.0 for row in dataset.rows)
    assert any(row.target == 1 for row in dataset.rows)
    assert all(
        row.lineage["threshold_version"]
        == "probabilistic-risk-thresholds-v3-2003-2017-quantiles"
        for row in dataset.rows
    )
    manifest = threshold_manifest(baseline)
    assert manifest["quantiles"] == {"yellow": 0.75, "orange": 0.9, "red": 0.975}
    assert manifest["regions"]["ken"]["observations"] == len(baseline)
    assert manifest["baseline_period"] == {
        "start": "2003-01-01",
        "end": "2023-02-28",
    }

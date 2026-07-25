from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import pytest

from mwangaza.gee.historical import _age_days
from mwangaza.probabilistic.backfill import (
    HistoricalSignalRow,
    dekadal_windows,
    last_complete_dekad,
    materialize_history,
)


@dataclass(frozen=True)
class _Region:
    id: str


class _Adapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def fetch(self, region, windows):
        self.calls.append((region.id, tuple(window.period_start for window in windows)))
        return tuple(
            HistoricalSignalRow(
                region_id=region.id,
                period_start=window.period_start,
                period_end=window.period_end,
                as_of=window.as_of,
                rainfall_mm=10.0,
                rainfall_available_days=(
                    date.fromisoformat(window.period_end)
                    - date.fromisoformat(window.period_start)
                ).days
                + 1,
                rainfall_observed_at=window.as_of,
                ndvi=0.4,
                ndvi_observed_at=window.period_start,
                ndvi_age_days=(
                    date.fromisoformat(window.period_end)
                    - date.fromisoformat(window.period_start)
                ).days,
                lst_c=31.0,
                lst_observed_at=window.period_start,
                lst_age_days=(
                    date.fromisoformat(window.period_end)
                    - date.fromisoformat(window.period_start)
                ).days,
                quality_flag="ok",
                missing_reasons=(),
                source_mode="live",
                geometry_version="v1",
            )
            for window in windows
        )


def test_dekadal_windows_cover_complete_periods_and_leap_year() -> None:
    windows = dekadal_windows(date(2024, 1, 1), date(2024, 2, 29))
    assert [(item.period_start, item.period_end) for item in windows] == [
        ("2024-01-01", "2024-01-10"),
        ("2024-01-11", "2024-01-20"),
        ("2024-01-21", "2024-01-31"),
        ("2024-02-01", "2024-02-10"),
        ("2024-02-11", "2024-02-20"),
        ("2024-02-21", "2024-02-29"),
    ]
    assert last_complete_dekad(date(2026, 7, 24)) == date(2026, 7, 20)
    assert last_complete_dekad(date(2026, 7, 5)) == date(2026, 6, 30)


def test_materialization_is_atomic_hashed_and_resumable(tmp_path) -> None:
    windows = dekadal_windows(date(2024, 1, 1), date(2024, 1, 31))
    adapter = _Adapter()
    manifest = materialize_history(
        regions=(_Region("ken"),),
        windows=windows,
        adapter=adapter,
        output_dir=tmp_path,
        chunk_size=2,
    )

    assert manifest.row_count == 3
    assert manifest.data_sha256.startswith("sha256:")
    assert len(adapter.calls) == 2
    rows = [
        json.loads(line)
        for line in (tmp_path / "history.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["period_start"] for row in rows] == [
        "2024-01-01",
        "2024-01-11",
        "2024-01-21",
    ]
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))[
        "data_sha256"
    ] == manifest.data_sha256

    resumed = _Adapter()
    second = materialize_history(
        regions=(_Region("ken"),),
        windows=windows,
        adapter=resumed,
        output_dir=tmp_path,
    )
    assert not resumed.calls
    assert second == manifest


def test_force_requeries_every_row(tmp_path) -> None:
    windows = dekadal_windows(date(2024, 1, 1), date(2024, 1, 31))
    materialize_history(
        regions=(_Region("ken"),), windows=windows, adapter=_Adapter(), output_dir=tmp_path
    )
    forced = _Adapter()
    materialize_history(
        regions=(_Region("ken"),),
        windows=windows,
        adapter=forced,
        output_dir=tmp_path,
        force=True,
    )
    assert sum(len(item[1]) for item in forced.calls) == 3


def test_modis_age_rejects_lookahead() -> None:
    assert _age_days("2024-01-17", "2024-01-20") == 3
    with pytest.raises(ValueError, match="future"):
        _age_days("2024-01-21", "2024-01-20")

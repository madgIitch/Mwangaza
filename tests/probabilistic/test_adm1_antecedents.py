from __future__ import annotations

import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from mwangaza.gee.adm1_antecedent import (
    EarthEngineAdm1AntecedentAdapter,
    _forecast_observation,
)
from mwangaza.probabilistic.adm1 import (
    Adm1DataError,
    Adm1RawRow,
    SignalObservation,
    materialize_adm1_history,
)
from mwangaza.probabilistic.antecedents import prepare_adm1_antecedents
from mwangaza.probabilistic.backfill import DekadalWindow, dekadal_windows
from mwangaza.regions import ADM1_LEVEL, list_regions


@dataclass(frozen=True)
class _Region:
    id: str
    parent_id: str
    iso3: str
    level: str
    source: str
    source_version: str
    geometry: dict[str, object]
    metadata: dict[str, str]


def _region(name: str) -> _Region:
    return _Region(
        id=name,
        parent_id="ken",
        iso3="KEN",
        level="adm1",
        source="geoBoundaries gbOpen",
        source_version="test-boundaries-v1",
        geometry={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        },
        metadata={"boundary_id": f"id-{name}", "boundary_iso": name.upper()},
    )


def _signal(
    value: float | int | None,
    *,
    unit: str,
    observed_at: str | None,
    reason: str | None = None,
) -> SignalObservation:
    return SignalObservation(
        value=value,
        unit=unit,
        source_collection="fixture",
        source_version="v1",
        observed_at=observed_at,
        available_at=observed_at,
        age_days=0 if observed_at else None,
        lead_hours=None,
        quality="observed" if value is not None else "missing",
        missing_reason=reason,
    )


def _raw_row(
    region: _Region,
    year: int,
    month: int,
    start_day: int,
    *,
    rain: float,
    ndvi: float | None,
) -> Adm1RawRow:
    end_day = 10 if start_day == 1 else 20 if start_day == 11 else monthrange(year, month)[1]
    start = date(year, month, start_day)
    end = date(year, month, end_day)
    as_of = datetime(end.year, end.month, end.day, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    days = (end - start).days + 1
    return Adm1RawRow(
        region_id=region.id,
        parent_region_id=region.parent_id,
        parent_iso3=region.iso3,
        boundary_id=region.metadata["boundary_id"],
        boundary_iso=region.metadata["boundary_iso"],
        boundary_source=region.source,
        boundary_version=region.source_version,
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        as_of=as_of,
        signals={
            "rainfall_mm": _signal(rain, unit="mm", observed_at=as_of),
            "rainfall_available_days": _signal(days, unit="days", observed_at=as_of),
            "ndvi": _signal(
                ndvi,
                unit="ndvi_fraction",
                observed_at=as_of if ndvi is not None else None,
                reason="ndvi_no_pixels" if ndvi is None else None,
            ),
        },
    )


class _BatchAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def fetch(
        self, regions: tuple[_Region, ...], windows: tuple[DekadalWindow, ...]
    ) -> tuple[Adm1RawRow, ...]:
        self.calls.append((len(regions), len(windows)))
        return tuple(
            _raw_row(
                region,
                date.fromisoformat(window.period_start).year,
                date.fromisoformat(window.period_start).month,
                date.fromisoformat(window.period_start).day,
                rain=10.0,
                ndvi=0.4,
            )
            for region in regions
            for window in windows
        )


def test_versioned_catalog_contains_exactly_121_adm1() -> None:
    regions = list_regions(level=ADM1_LEVEL, include_administrative=True)
    assert len(regions) == 121
    assert len({region.id for region in regions}) == 121
    assert all(region.metadata["boundary_id"] for region in regions)
    assert all(region.geometry["type"] in {"Polygon", "MultiPolygon"} for region in regions)


def test_adm1_materialization_batches_regions_resumes_and_hashes(tmp_path) -> None:
    regions = tuple(_region(f"adm1-{index}") for index in range(121))
    windows = dekadal_windows(date(2024, 1, 1), date(2024, 1, 31))
    adapter = _BatchAdapter()
    manifest = materialize_adm1_history(
        regions=regions,
        windows=windows,
        adapter=adapter,
        output_dir=tmp_path,
        region_batch_size=32,
        window_chunk_size=3,
    )
    assert manifest.row_count == 363
    assert manifest.region_count == 121
    assert len(adapter.calls) == 4
    assert all(region.geometry for region in manifest.regions)
    assert manifest.data_sha256.startswith("sha256:")
    serialized = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert "private_key" not in serialized
    assert json.loads(serialized)["region_count"] == 121

    resumed = _BatchAdapter()
    assert (
        materialize_adm1_history(
            regions=regions,
            windows=windows,
            adapter=resumed,
            output_dir=tmp_path,
        )
        == manifest
    )
    assert not resumed.calls


def test_materialization_rejects_future_availability(tmp_path) -> None:
    class _UnsafeAdapter(_BatchAdapter):
        def fetch(self, regions, windows):
            row = super().fetch(regions, windows)[0]
            signals = dict(row.signals)
            signals["ndvi"] = SignalObservation(
                value=0.4,
                unit="ndvi_fraction",
                source_collection="fixture",
                source_version="v1",
                observed_at=row.as_of,
                available_at="2099-01-01T00:00:00Z",
                age_days=0,
                lead_hours=None,
                quality="observed",
            )
            return (Adm1RawRow(**{**row.__dict__, "signals": signals}),)

    with pytest.raises(Adm1DataError, match="unavailable"):
        materialize_adm1_history(
            regions=(_region("adm1-one"),),
            windows=dekadal_windows(date(2024, 1, 1), date(2024, 1, 10)),
            adapter=_UnsafeAdapter(),
            output_dir=tmp_path,
        )


def test_empirical_spi_uses_only_pre_cut_reference_and_months_are_complete() -> None:
    region = _region("adm1-one")
    history = tuple(
        _raw_row(
            region,
            year,
            month,
            day,
            rain=(month * 2 + year % 7) / 3,
            ndvi=0.5 + (year % 5) * 0.01,
        )
        for year in range(2003, 2019)
        for month in range(1, 13)
        for day in (1, 11, 21)
    )
    prepared = prepare_adm1_antecedents(
        history, reference_end=date(2017, 12, 31), min_reference_years=15
    )
    target = next(row for row in prepared if row.period_start == "2018-12-21")
    original_spi = target.signals["spi_1m"].value
    assert original_spi is not None
    assert target.signals["spi_6m"].value is not None
    assert target.signals["rainfall_deficit_3m_mm"].value is not None

    future = tuple(
        _raw_row(region, 2019, month, day, rain=100_000.0, ndvi=0.9)
        for month in range(1, 13)
        for day in (1, 11, 21)
    )
    with_future = prepare_adm1_antecedents(
        (*history, *future), reference_end=date(2017, 12, 31), min_reference_years=15
    )
    same_target = next(row for row in with_future if row.period_start == "2018-12-21")
    assert same_target.signals["spi_1m"].value == original_spi

    first_dekad = next(row for row in prepared if row.period_start == "2018-12-01")
    assert first_dekad.signals["spi_1m"].observed_at.startswith("2018-11-30")


def test_ndvi_trajectory_marks_gaps_and_computes_velocity() -> None:
    region = _region("adm1-one")
    baseline = tuple(
        _raw_row(region, year, 1, day, rain=10, ndvi=0.6)
        for year in range(2003, 2018)
        for day in (1, 11, 21)
    )
    current = (
        _raw_row(region, 2018, 1, 1, rain=5, ndvi=0.5),
        _raw_row(region, 2018, 1, 11, rain=5, ndvi=0.4),
        _raw_row(region, 2018, 1, 21, rain=5, ndvi=0.3),
    )
    prepared = prepare_adm1_antecedents(
        (*baseline, *current), reference_end=date(2017, 12, 31), min_reference_years=15
    )
    target = next(row for row in prepared if row.period_start == "2018-01-21")
    assert target.signals["ndvi_slope_3dekad"].value == pytest.approx(-0.1)
    assert target.signals["ndvi_decline_persistence_dekads"].value == 3

    gapped = prepare_adm1_antecedents(
        (*baseline, current[0], current[2]),
        reference_end=date(2017, 12, 31),
        min_reference_years=15,
    )
    target_gapped = next(row for row in gapped if row.period_start == "2018-01-21")
    assert target_gapped.signals["ndvi_slope_3dekad"].missing_reason in {
        "dekadal_gap",
        "incomplete_ndvi_window",
    }


def test_fldas_units_and_forecast_temporal_contract() -> None:
    adapter = EarthEngineAdm1AntecedentAdapter(object())
    region = _region("adm1-one")
    window = DekadalWindow(
        period_start="2025-01-01",
        period_end="2025-01-10",
        as_of="2025-01-10T00:00:00Z",
    )
    values = {
        "rainfall_mm": 10,
        "rainfall_available_days": 10,
        "ndvi": 0.4,
        "ndvi_observed_at_ms": 1_734_480_000_000,
        "spei_1m": -1,
        "spei_3m": -0.5,
        "spei_6m": -0.2,
        "spei_observed_at_ms": 1_733_011_200_000,
        "soil_moisture_0_10cm": 0.2,
        "soil_moisture_rootzone": 0.3,
        "evapotranspiration_rate": 0.00001,
        "fldas_observed_at_ms": 1_733_011_200_000,
        "forecast_precip_10d_mm": 20,
        "forecast_10d_creation_ms": 1_736_467_200_000,
        "forecast_precip_15d_mm": 25,
        "forecast_15d_creation_ms": 1_736_467_200_000,
    }
    row = adapter._row(region, window, values)
    assert row.signals["soil_moisture_0_10cm"].unit == "volume_fraction"
    assert row.signals["evapotranspiration_rate"].unit == "kg/m^2/s"
    assert row.signals["ndvi"].available_at <= row.as_of
    assert row.signals["forecast_precip_10d_mm"].lead_hours == 240
    assert row.signals["forecast_precip_10d_mm"].observed_at is None

    before = _forecast_observation(
        10,
        creation=datetime(2024, 11, 1, tzinfo=UTC),
        as_of=datetime(2024, 11, 10, tzinfo=UTC),
        lead_hours=240,
    )
    assert before.value is None
    assert before.missing_reason == "not_available_for_date"

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import NormalDist, fmean
from typing import Callable, Iterable

from mwangaza.probabilistic.adm1 import Adm1PreparedRow, Adm1RawRow, SignalObservation

ANTECEDENT_TRANSFORMATION_VERSION = "adm1-antecedents-empirical-spi-v1"
SPI_SCALES = (1, 3, 6)


@dataclass(frozen=True)
class _MonthlyRain:
    region_id: str
    year: int
    month: int
    total_mm: float
    observed_at: str

    @property
    def key(self) -> tuple[str, int, int]:
        return self.region_id, self.year, self.month


def prepare_adm1_antecedents(
    rows: tuple[Adm1RawRow, ...],
    *,
    reference_end: date,
    min_reference_years: int = 15,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[Adm1PreparedRow, ...]:
    if min_reference_years < 3:
        raise ValueError("min_reference_years must be at least 3")
    ordered = tuple(sorted(rows, key=lambda row: (row.region_id, row.period_start)))
    _validate_unique_rows(ordered)
    monthly = _complete_monthly_rain(ordered)
    monthly_by_key = {item.key: item for item in monthly}
    spi_reference = _spi_reference(
        monthly,
        reference_end=reference_end,
        min_reference_years=min_reference_years,
    )
    ndvi_reference = _ndvi_reference(
        ordered,
        reference_end=reference_end,
        min_reference_years=min_reference_years,
    )
    region_rows: dict[str, list[Adm1RawRow]] = defaultdict(list)
    for row in ordered:
        region_rows[row.region_id].append(row)

    result: list[Adm1PreparedRow] = []
    completed = 0
    for region_id in sorted(region_rows):
        history = region_rows[region_id]
        for index, row in enumerate(history):
            signals = dict(row.signals)
            latest_month = _latest_complete_month(row, monthly_by_key)
            for scale in SPI_SCALES:
                current = _rolling_rain(monthly_by_key, region_id, latest_month, scale)
                reference = (
                    None
                    if latest_month is None
                    else spi_reference.get((region_id, latest_month[1], scale))
                )
                signals[f"spi_{scale}m"] = _spi_signal(
                    current=current,
                    reference=reference,
                    scale=scale,
                    as_of=row.as_of,
                )
                signals[f"rainfall_deficit_{scale}m_mm"] = _deficit_signal(
                    current=current,
                    reference=reference,
                    scale=scale,
                    as_of=row.as_of,
                )
            signals.update(_ndvi_features(history, index, ndvi_reference))
            result.append(
                Adm1PreparedRow(
                    region_id=row.region_id,
                    parent_region_id=row.parent_region_id,
                    parent_iso3=row.parent_iso3,
                    boundary_id=row.boundary_id,
                    boundary_iso=row.boundary_iso,
                    boundary_source=row.boundary_source,
                    boundary_version=row.boundary_version,
                    period_start=row.period_start,
                    period_end=row.period_end,
                    as_of=row.as_of,
                    signals=signals,
                    transformation_version=ANTECEDENT_TRANSFORMATION_VERSION,
                )
            )
            completed += 1
            if progress:
                progress(completed, len(ordered))
    return tuple(result)


def _complete_monthly_rain(rows: tuple[Adm1RawRow, ...]) -> tuple[_MonthlyRain, ...]:
    grouped: dict[tuple[str, int, int], list[Adm1RawRow]] = defaultdict(list)
    for row in rows:
        value = date.fromisoformat(row.period_start)
        grouped[(row.region_id, value.year, value.month)].append(row)
    result: list[_MonthlyRain] = []
    for (region_id, year, month), values in grouped.items():
        ordered = sorted(values, key=lambda row: row.period_start)
        expected_starts = (1, 11, 21)
        if tuple(date.fromisoformat(row.period_start).day for row in ordered) != expected_starts:
            continue
        signals = [row.signals.get("rainfall_mm") for row in ordered]
        if any(signal is None or signal.value is None for signal in signals):
            continue
        available_days = [
            row.signals.get("rainfall_available_days") for row in ordered
        ]
        if any(signal is None or signal.value is None for signal in available_days):
            continue
        if sum(int(signal.value) for signal in available_days if signal is not None) != monthrange(
            year, month
        )[1]:
            continue
        total = sum(float(signal.value) for signal in signals if signal is not None)
        result.append(
            _MonthlyRain(
                region_id=region_id,
                year=year,
                month=month,
                total_mm=total,
                observed_at=date(year, month, monthrange(year, month)[1]).isoformat(),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.region_id, item.year, item.month)))


def _spi_reference(
    monthly: tuple[_MonthlyRain, ...],
    *,
    reference_end: date,
    min_reference_years: int,
) -> dict[tuple[str, int, int], tuple[float, ...]]:
    by_key = {item.key: item for item in monthly}
    grouped: dict[tuple[str, int, int], list[float]] = defaultdict(list)
    for item in monthly:
        if date(item.year, item.month, monthrange(item.year, item.month)[1]) > reference_end:
            continue
        latest = (item.year, item.month)
        for scale in SPI_SCALES:
            accumulated = _rolling_rain(by_key, item.region_id, latest, scale)
            if accumulated is not None:
                grouped[(item.region_id, item.month, scale)].append(accumulated[0])
    return {
        key: tuple(sorted(values))
        for key, values in grouped.items()
        if len(values) >= min_reference_years
    }


def _rolling_rain(
    monthly: dict[tuple[str, int, int], _MonthlyRain],
    region_id: str,
    latest: tuple[int, int] | None,
    scale: int,
) -> tuple[float, str] | None:
    if latest is None:
        return None
    cursor = date(latest[0], latest[1], 1)
    values: list[_MonthlyRain] = []
    for _ in range(scale):
        item = monthly.get((region_id, cursor.year, cursor.month))
        if item is None:
            return None
        values.append(item)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return sum(item.total_mm for item in values), values[0].observed_at


def _latest_complete_month(
    row: Adm1RawRow,
    monthly: dict[tuple[str, int, int], _MonthlyRain],
) -> tuple[int, int] | None:
    as_of = _parse_datetime(row.as_of).date()
    cursor = date(as_of.year, as_of.month, 1)
    if as_of.day < monthrange(as_of.year, as_of.month)[1]:
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for _ in range(7):
        if (row.region_id, cursor.year, cursor.month) in monthly:
            return cursor.year, cursor.month
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return None


def _spi_signal(
    *,
    current: tuple[float, str] | None,
    reference: tuple[float, ...] | None,
    scale: int,
    as_of: str,
) -> SignalObservation:
    if current is None:
        return _derived_missing("CHIRPS empirical SPI", "mm→z", "incomplete_month_window")
    if reference is None:
        return _derived_missing("CHIRPS empirical SPI", "mm→z", "insufficient_reference")
    less = sum(value < current[0] for value in reference)
    equal = sum(value == current[0] for value in reference)
    probability = (less + 0.5 * equal + 0.5) / (len(reference) + 1)
    probability = min(1 - 1e-7, max(1e-7, probability))
    value = NormalDist().inv_cdf(probability)
    return _derived_signal(
        value=round(value, 6),
        unit="z_score",
        source=f"CHIRPS empirical SPI {scale}m",
        observed_at=current[1],
        as_of=as_of,
    )


def _deficit_signal(
    *,
    current: tuple[float, str] | None,
    reference: tuple[float, ...] | None,
    scale: int,
    as_of: str,
) -> SignalObservation:
    if current is None:
        return _derived_missing("CHIRPS rainfall deficit", "mm", "incomplete_month_window")
    if reference is None:
        return _derived_missing("CHIRPS rainfall deficit", "mm", "insufficient_reference")
    return _derived_signal(
        value=round(max(0.0, fmean(reference) - current[0]), 6),
        unit="mm",
        source=f"CHIRPS rainfall deficit {scale}m",
        observed_at=current[1],
        as_of=as_of,
    )


def _ndvi_reference(
    rows: tuple[Adm1RawRow, ...],
    *,
    reference_end: date,
    min_reference_years: int,
) -> dict[tuple[str, int], float]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in rows:
        if date.fromisoformat(row.period_end) > reference_end:
            continue
        signal = row.signals.get("ndvi")
        if signal is None or signal.value is None:
            continue
        grouped[(row.region_id, _dekad_of_year(row.period_start))].append(float(signal.value))
    return {
        key: fmean(values)
        for key, values in grouped.items()
        if len(values) >= min_reference_years
    }


def _ndvi_features(
    rows: list[Adm1RawRow],
    index: int,
    reference: dict[tuple[str, int], float],
) -> dict[str, SignalObservation]:
    row = rows[index]
    current = row.signals.get("ndvi")
    current_mean = reference.get((row.region_id, _dekad_of_year(row.period_start)))
    if current is None or current.value is None:
        reason = current.missing_reason if current is not None else "ndvi_no_data"
        missing = _derived_missing("MOD13Q1 NDVI trajectory", "dekads", reason or "ndvi_no_data")
        return {
            "ndvi_anomaly": _derived_missing(
                "MOD13Q1 NDVI climatology", "ndvi_fraction", reason or "ndvi_no_data"
            ),
            "ndvi_decline_persistence_dekads": missing,
            "ndvi_slope_3dekad": _derived_missing(
                "MOD13Q1 NDVI trajectory", "ndvi_fraction/dekad", reason or "ndvi_no_data"
            ),
            "ndvi_slope_6dekad": _derived_missing(
                "MOD13Q1 NDVI trajectory", "ndvi_fraction/dekad", reason or "ndvi_no_data"
            ),
        }
    if current_mean is None:
        anomaly = _derived_missing(
            "MOD13Q1 NDVI climatology", "ndvi_fraction", "insufficient_reference"
        )
    else:
        anomaly = _derived_signal(
            value=round(float(current.value) - current_mean, 6),
            unit="ndvi_fraction",
            source="MOD13Q1 seasonal ADM1 climatology",
            observed_at=current.observed_at or row.period_end,
            as_of=row.as_of,
        )

    persistence = 0
    persistence_reason: str | None = None
    for cursor in range(index, -1, -1):
        item = rows[cursor]
        if cursor < index and not _contiguous(item, rows[cursor + 1]):
            persistence_reason = "dekadal_gap"
            break
        signal = item.signals.get("ndvi")
        baseline = reference.get((item.region_id, _dekad_of_year(item.period_start)))
        if signal is None or signal.value is None or baseline is None:
            persistence_reason = "incomplete_ndvi_window"
            break
        if float(signal.value) - baseline >= 0:
            break
        persistence += 1
    persistence_signal = _derived_signal(
        value=persistence,
        unit="dekads",
        source="MOD13Q1 negative-anomaly persistence",
        observed_at=current.observed_at or row.period_end,
        as_of=row.as_of,
    )
    if persistence == 0 and persistence_reason:
        persistence_signal = _derived_missing(
            "MOD13Q1 negative-anomaly persistence", "dekads", persistence_reason
        )
    return {
        "ndvi_anomaly": anomaly,
        "ndvi_decline_persistence_dekads": persistence_signal,
        "ndvi_slope_3dekad": _ndvi_slope(rows, index, 3),
        "ndvi_slope_6dekad": _ndvi_slope(rows, index, 6),
    }


def _ndvi_slope(rows: list[Adm1RawRow], index: int, size: int) -> SignalObservation:
    start = index - size + 1
    if start < 0:
        return _derived_missing(
            "MOD13Q1 NDVI trajectory", "ndvi_fraction/dekad", "incomplete_ndvi_window"
        )
    window = rows[start : index + 1]
    if any(not _contiguous(left, right) for left, right in zip(window, window[1:])):
        return _derived_missing(
            "MOD13Q1 NDVI trajectory", "ndvi_fraction/dekad", "dekadal_gap"
        )
    signals = [row.signals.get("ndvi") for row in window]
    if any(signal is None or signal.value is None for signal in signals):
        return _derived_missing(
            "MOD13Q1 NDVI trajectory", "ndvi_fraction/dekad", "incomplete_ndvi_window"
        )
    values = [float(signal.value) for signal in signals if signal is not None]
    mean_x = (size - 1) / 2
    mean_y = fmean(values)
    denominator = sum((x - mean_x) ** 2 for x in range(size))
    slope = sum((x - mean_x) * (value - mean_y) for x, value in enumerate(values))
    observed_at = signals[-1].observed_at if signals[-1] is not None else window[-1].period_end
    return _derived_signal(
        value=round(slope / denominator, 6),
        unit="ndvi_fraction/dekad",
        source=f"MOD13Q1 OLS trajectory {size} dekads",
        observed_at=observed_at or window[-1].period_end,
        as_of=window[-1].as_of,
    )


def _derived_signal(
    *,
    value: float | int,
    unit: str,
    source: str,
    observed_at: str,
    as_of: str,
) -> SignalObservation:
    observed = _parse_datetime(observed_at)
    available = _parse_datetime(as_of)
    return SignalObservation(
        value=value,
        unit=unit,
        source_collection=source,
        source_version=ANTECEDENT_TRANSFORMATION_VERSION,
        observed_at=_iso(observed),
        available_at=_iso(available),
        age_days=max(0, (available.date() - observed.date()).days),
        lead_hours=None,
        quality="derived",
    )


def _derived_missing(source: str, unit: str, reason: str) -> SignalObservation:
    return SignalObservation(
        value=None,
        unit=unit,
        source_collection=source,
        source_version=ANTECEDENT_TRANSFORMATION_VERSION,
        observed_at=None,
        available_at=None,
        age_days=None,
        lead_hours=None,
        quality="missing",
        missing_reason=reason,
    )


def _validate_unique_rows(rows: Iterable[Adm1RawRow]) -> None:
    seen: set[str] = set()
    for row in rows:
        if row.key in seen:
            raise ValueError(f"duplicate row: {row.key}")
        seen.add(row.key)


def _contiguous(left: Adm1RawRow, right: Adm1RawRow) -> bool:
    return date.fromisoformat(left.period_end) + timedelta(days=1) == date.fromisoformat(
        right.period_start
    )


def _dekad_of_year(period_start: str) -> int:
    value = date.fromisoformat(period_start)
    dekad = 1 if value.day <= 10 else 2 if value.day <= 20 else 3
    return (value.month - 1) * 3 + dekad


def _parse_datetime(value: str) -> datetime:
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")

from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from mwangaza.config import load_settings
from mwangaza.contracts import Baseline
from mwangaza.data.ndvi import DEFAULT_NDVI_COLLECTION
from mwangaza.regions import get_region


class ClimatologyError(ValueError):
    pass


@dataclass(frozen=True)
class ClimatologyConfig:
    start_year: int
    end_year: int
    min_years: int = 10
    collection_id: str = DEFAULT_NDVI_COLLECTION

    @classmethod
    def from_settings(cls) -> ClimatologyConfig:
        settings = load_settings()
        return cls(
            start_year=settings.climatology_start_year,
            end_year=settings.climatology_end_year,
            min_years=settings.climatology_min_years,
            collection_id=settings.ndvi_collection,
        )


@dataclass(frozen=True)
class ClimatologyYearObservation:
    year: int
    value: float | None
    quality_flag: str = "ok"
    source: str | None = None
    metadata: dict[str, Any] | None = None


class ClimatologyAdapter(Protocol):
    def query_ndvi_year(
        self,
        geometry: dict[str, Any],
        year: int,
        season_start: str,
        season_end: str,
        config: ClimatologyConfig,
    ) -> ClimatologyYearObservation:
        ...


def compute_ndvi_climatology(
    region_id: str,
    season_start: str,
    season_end: str,
    current_period_start: str,
    current_period_end: str,
    *,
    adapter: ClimatologyAdapter,
    config: ClimatologyConfig | None = None,
) -> Baseline:
    resolved_config = config or ClimatologyConfig.from_settings()
    _validate_config(resolved_config)
    current_start = _parse_datetime(current_period_start, "current_period_start")
    current_end = _parse_datetime(current_period_end, "current_period_end")
    if current_start > current_end:
        raise ClimatologyError("current period is inverted")

    season_start_month, season_start_day = _parse_month_day(season_start, "season_start")
    season_end_month, season_end_day = _parse_month_day(season_end, "season_end")
    region = get_region(region_id)
    current_year = current_start.year

    effective_years: list[int] = []
    excluded_years: list[int] = []
    values: list[float] = []

    for year in range(resolved_config.start_year, resolved_config.end_year + 1):
        _season_dates_for_year(year, season_start_month, season_start_day, season_end_month, season_end_day)
        if year == current_year:
            excluded_years.append(year)
            continue
        observation = adapter.query_ndvi_year(region.geometry, year, season_start, season_end, resolved_config)
        if observation.year != year:
            raise ClimatologyError("adapter returned observation for the wrong year")
        if observation.value is None or observation.quality_flag != "ok":
            excluded_years.append(year)
            continue
        if not math.isfinite(observation.value) or not -1.0 <= observation.value <= 1.0:
            raise ClimatologyError("NDVI climatology values must be finite and inside [-1.0, 1.0]")
        effective_years.append(year)
        values.append(float(observation.value))

    metadata = _metadata(
        region_id=region.id,
        config=resolved_config,
        season_start=season_start,
        season_end=season_end,
        effective_years=effective_years,
        excluded_years=excluded_years,
    )
    period_start, period_end = _baseline_period(
        resolved_config,
        season_start_month,
        season_start_day,
        season_end_month,
        season_end_day,
    )

    if len(values) < resolved_config.min_years:
        return Baseline(
            region_id=region.id,
            indicator="ndvi",
            period_start=period_start,
            period_end=period_end,
            baseline_start_year=resolved_config.start_year,
            baseline_end_year=resolved_config.end_year,
            mean=None,
            median=None,
            stddev=None,
            observations=len(values),
            unit="index",
            source=resolved_config.collection_id,
            quality_flag="insufficient_history",
            is_simulated=False,
            metadata=metadata,
        )

    return Baseline(
        region_id=region.id,
        indicator="ndvi",
        period_start=period_start,
        period_end=period_end,
        baseline_start_year=resolved_config.start_year,
        baseline_end_year=resolved_config.end_year,
        mean=statistics.fmean(values),
        median=statistics.median(values),
        stddev=statistics.pstdev(values),
        observations=len(values),
        unit="index",
        source=resolved_config.collection_id,
        quality_flag="ok",
        is_simulated=False,
        metadata=metadata,
    )


def _validate_config(config: ClimatologyConfig) -> None:
    if config.start_year > config.end_year:
        raise ClimatologyError("climatology year window is inverted")
    if config.min_years <= 0:
        raise ClimatologyError("min_years must be positive")
    if not config.collection_id:
        raise ClimatologyError("collection_id is required")


def _parse_month_day(value: str, field_name: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise ClimatologyError(f"{field_name} must use MM-DD format")
    try:
        month, day = int(parts[0]), int(parts[1])
        date(2001, month, day)
    except ValueError as exc:
        raise ClimatologyError(f"{field_name} is not a valid month-day") from exc
    return month, day


def _season_dates_for_year(
    year: int,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
) -> tuple[date, date]:
    try:
        start = date(year, start_month, start_day)
        end_year = year + 1 if (end_month, end_day) < (start_month, start_day) else year
        end = date(end_year, end_month, end_day)
    except ValueError as exc:
        raise ClimatologyError("season day is invalid for a climatology year") from exc
    if start > end:
        raise ClimatologyError("season window is inverted")
    return start, end


def _baseline_period(
    config: ClimatologyConfig,
    start_month: int,
    start_day: int,
    end_month: int,
    end_day: int,
) -> tuple[str, str]:
    start, _ = _season_dates_for_year(config.start_year, start_month, start_day, end_month, end_day)
    _, end = _season_dates_for_year(config.end_year, start_month, start_day, end_month, end_day)
    return f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T00:00:00Z"


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClimatologyError(f"{field_name} must be ISO8601") from exc


def _metadata(
    *,
    region_id: str,
    config: ClimatologyConfig,
    season_start: str,
    season_end: str,
    effective_years: list[int],
    excluded_years: list[int],
) -> dict[str, Any]:
    period_key = f"{season_start}_{season_end}"
    version_input = "|".join(
        [
            region_id,
            "ndvi",
            str(config.start_year),
            str(config.end_year),
            season_start,
            season_end,
            config.collection_id,
        ]
    )
    return {
        "effective_years": list(effective_years),
        "excluded_years": list(excluded_years),
        "min_years": config.min_years,
        "season_start": season_start,
        "season_end": season_end,
        "period_key": period_key,
        "baseline_version": hashlib.sha256(version_input.encode("utf-8")).hexdigest()[:16],
        "collection_id": config.collection_id,
    }

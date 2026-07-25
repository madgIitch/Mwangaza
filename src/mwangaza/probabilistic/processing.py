from __future__ import annotations

import json
import math
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, pstdev
from typing import Callable

from mwangaza.probabilistic.backfill import HistoricalSignalRow
from mwangaza.probabilistic.dataset import (
    HistoricalRiskPeriod,
    TrainingDataset,
    build_training_dataset,
)

CLIMATOLOGY_VERSION = "igad-dekadal-2003-2017-v2"
SCORE_VERSION = "probabilistic-composite-v1"
THRESHOLD_VERSION = "probabilistic-risk-thresholds-v3-2003-2017-quantiles"


@dataclass(frozen=True)
class SeasonalStats:
    count: int
    mean: float
    stddev: float


@dataclass(frozen=True)
class RiskThresholds:
    yellow: float
    orange: float
    red: float
    observations: int


def load_signal_rows(path: Path) -> tuple[HistoricalSignalRow, ...]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line, parse_constant=_reject_constant)
        payload["missing_reasons"] = tuple(payload["missing_reasons"])
        rows.append(HistoricalSignalRow(**payload))
    return tuple(rows)


def build_real_training_dataset(
    current_rows: tuple[HistoricalSignalRow, ...],
    baseline_rows: tuple[HistoricalSignalRow, ...],
    *,
    min_baseline_years: int = 15,
    progress: Callable[[int, int], None] | None = None,
) -> TrainingDataset:
    climatology = _climatology(baseline_rows, min_baseline_years)
    thresholds = _risk_thresholds(baseline_rows, climatology)
    observations: list[HistoricalRiskPeriod] = []
    for index, row in enumerate(current_rows, 1):
        observations.append(_risk_period(row, climatology, thresholds))
        if progress is not None:
            progress(index, len(current_rows))
    return build_training_dataset(observations)


def threshold_manifest(
    baseline_rows: tuple[HistoricalSignalRow, ...],
    *,
    min_baseline_years: int = 15,
) -> dict[str, object]:
    climatology = _climatology(baseline_rows, min_baseline_years)
    thresholds = _risk_thresholds(baseline_rows, climatology)
    return {
        "schema_version": "mwangaza.probabilistic-risk-thresholds.v1",
        "threshold_version": THRESHOLD_VERSION,
        "baseline_period": {
            "start": min(row.period_start for row in baseline_rows),
            "end": max(row.period_end for row in baseline_rows),
        },
        "quantiles": {"yellow": 0.75, "orange": 0.90, "red": 0.975},
        "regions": {
            region: {
                "yellow": value.yellow,
                "orange": value.orange,
                "red": value.red,
                "observations": value.observations,
            }
            for region, value in sorted(thresholds.items())
        },
    }


def write_threshold_manifest(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _climatology(
    rows: tuple[HistoricalSignalRow, ...], min_years: int
) -> dict[tuple[str, int, str], SeasonalStats]:
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        season = _season_index(row.period_start)
        for name, value in (
            ("rainfall_mm", row.rainfall_mm),
            ("ndvi", row.ndvi),
            ("lst_c", row.lst_c),
        ):
            if value is not None and math.isfinite(value):
                grouped[(row.region_id, season, name)].append(value)
    result = {}
    for key, values in grouped.items():
        if len(values) < min_years:
            continue
        result[key] = SeasonalStats(
            count=len(values),
            mean=fmean(values),
            stddev=pstdev(values),
        )
    return result


def _risk_period(
    row: HistoricalSignalRow,
    climatology: dict[tuple[str, int, str], SeasonalStats],
    thresholds: dict[str, RiskThresholds],
) -> HistoricalRiskPeriod:
    score, zscores, quality = _score(row, climatology)
    resolved = thresholds.get(row.region_id)
    if score is None or resolved is None:
        level = "unknown"
    else:
        level = _level(score, resolved)

    signal_observed_at = {}
    if row.rainfall_observed_at:
        signal_observed_at["rainfall_mm"] = _parse_time(row.rainfall_observed_at)
    if row.ndvi_observed_at:
        signal_observed_at["ndvi"] = _parse_time(row.ndvi_observed_at)
    if row.lst_observed_at:
        signal_observed_at["lst_c"] = _parse_time(row.lst_observed_at)
    return HistoricalRiskPeriod(
        region_id=row.region_id,
        as_of=_parse_time(row.as_of),
        frequency="dekadal",
        risk_level=level,
        quality_flag=quality,
        threshold_version=THRESHOLD_VERSION,
        source_version="CHIRPS-Daily+MOD13Q1+MOD11A2",
        transformation_version=CLIMATOLOGY_VERSION,
        score_version=SCORE_VERSION,
        geometry_version=row.geometry_version,
        signals={
            "risk_score": score,
            "rainfall_mm": row.rainfall_mm,
            "rainfall_anomaly": zscores["rainfall_mm"],
            "ndvi": row.ndvi,
            "ndvi_anomaly": zscores["ndvi"],
            "lst_c": row.lst_c,
            "lst_anomaly": zscores["lst_c"],
        },
        signal_observed_at=signal_observed_at,
    )


def _score(
    row: HistoricalSignalRow,
    climatology: dict[tuple[str, int, str], SeasonalStats],
) -> tuple[float | None, dict[str, float | None], str]:
    season = _season_index(row.period_start)
    values = {
        "rainfall_mm": row.rainfall_mm,
        "ndvi": row.ndvi,
        "lst_c": row.lst_c,
    }
    zscores: dict[str, float | None] = {}
    for name, value in values.items():
        stats = climatology.get((row.region_id, season, name))
        zscores[name] = (
            None
            if value is None or stats is None or stats.stddev <= 1e-12
            else (value - stats.mean) / stats.stddev
        )

    required = (zscores["rainfall_mm"], zscores["ndvi"])
    if any(value is None for value in required):
        score = None
        quality = "insufficient_history" if not row.missing_reasons else "no_data"
    else:
        rain = _severity(-float(zscores["rainfall_mm"]))
        ndvi = _severity(-float(zscores["ndvi"]))
        lst = _severity(float(zscores["lst_c"])) if zscores["lst_c"] is not None else None
        weights = {"rain": 0.4, "ndvi": 0.4, "lst": 0.2}
        if lst is None:
            weights = {"rain": 0.5, "ndvi": 0.5}
        score = rain * weights["rain"] + ndvi * weights["ndvi"]
        if lst is not None:
            score += lst * weights["lst"]
        score = round(score, 6)
        quality = "ok"
    return score, zscores, quality


def _severity(adverse_z: float) -> float:
    return min(100.0, max(0.0, adverse_z / 3.0 * 100.0))


def _risk_thresholds(
    rows: tuple[HistoricalSignalRow, ...],
    climatology: dict[tuple[str, int, str], SeasonalStats],
) -> dict[str, RiskThresholds]:
    scores: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        score, _, quality = _score(row, climatology)
        if score is not None and quality == "ok":
            scores[row.region_id].append(score)
    result = {}
    for region, values in scores.items():
        if len(values) < 100:
            continue
        ordered = sorted(values)
        result[region] = RiskThresholds(
            yellow=round(_percentile(ordered, 0.75), 6),
            orange=round(_percentile(ordered, 0.90), 6),
            red=round(_percentile(ordered, 0.975), 6),
            observations=len(ordered),
        )
    return result


def _percentile(values: list[float], quantile: float) -> float:
    position = (len(values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _level(score: float, thresholds: RiskThresholds) -> str:
    if score >= thresholds.red:
        return "red"
    if score >= thresholds.orange:
        return "orange"
    if score >= thresholds.yellow:
        return "yellow"
    return "green"


def _season_index(period_start: str) -> int:
    value = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
    dekad = 1 if value.day <= 10 else 2 if value.day <= 20 else 3
    return (value.month - 1) * 3 + dekad


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")

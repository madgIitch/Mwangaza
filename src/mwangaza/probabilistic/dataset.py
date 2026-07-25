from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, cast

SCHEMA_VERSION = "mwangaza.probabilistic-training.v1"
FEATURE_MANIFEST_VERSION = "mwangaza.probabilistic-features.v1.1"
SUPPORTED_FREQUENCIES = {"monthly", "dekadal"}
PREFERRED_FREQUENCY = "dekadal"
KNOWN_LEVELS = {"green", "yellow", "orange", "red", "unknown"}
BLOCKING_QUALITY = {"invalid", "no_data", "insufficient_history", "blocked", "critical"}
DEFAULT_SIGNAL_NAMES = (
    "ndvi",
    "ndvi_anomaly",
    "ndvi_anomaly_percent",
    "ndvi_zscore",
    "rainfall_mm",
    "rainfall_anomaly",
    "rainfall_percentile",
    "lst_c",
    "lst_anomaly",
    "risk_score",
    "quality_score",
    "spatial_coverage",
    "temporal_coverage",
)


class DatasetValidationError(ValueError):
    """Raised when an input cannot form a scientifically valid dataset."""


@dataclass(frozen=True)
class HistoricalRiskPeriod:
    region_id: str
    as_of: datetime
    frequency: str
    risk_level: str
    quality_flag: str
    threshold_version: str
    source_version: str
    transformation_version: str
    score_version: str
    geometry_version: str
    signals: Mapping[str, float | None] = field(default_factory=dict)
    signal_observed_at: Mapping[str, datetime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "signals", MappingProxyType(dict(self.signals)))
        object.__setattr__(
            self, "signal_observed_at", MappingProxyType(dict(self.signal_observed_at))
        )
        _validate_observation(self)


@dataclass(frozen=True)
class DatasetConfig:
    horizons: tuple[int, ...] = (1, 2, 3)
    signal_names: tuple[str, ...] = DEFAULT_SIGNAL_NAMES
    schema_version: str = SCHEMA_VERSION
    feature_manifest_version: str = FEATURE_MANIFEST_VERSION

    def __post_init__(self) -> None:
        if not self.horizons or any(value not in {1, 2, 3} for value in self.horizons):
            raise DatasetValidationError("horizons must contain only 1, 2 and 3")
        if len(set(self.horizons)) != len(self.horizons):
            raise DatasetValidationError("horizons must be unique")
        if not self.signal_names or len(set(self.signal_names)) != len(self.signal_names):
            raise DatasetValidationError("signal_names must be non-empty and unique")
        if any(not name or not name.replace("_", "").isalnum() for name in self.signal_names):
            raise DatasetValidationError("signal_names must use alphanumeric snake_case names")


@dataclass(frozen=True)
class TrainingRow:
    region_id: str
    as_of: str
    horizon_periods: int
    horizon_days: int | None
    target: int | None
    target_reason: str
    target_as_of: str | None
    features: Mapping[str, float | None]
    feature_reasons: tuple[str, ...]
    lineage: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "features", MappingProxyType(dict(self.features)))
        object.__setattr__(self, "lineage", MappingProxyType(dict(self.lineage)))


@dataclass(frozen=True)
class TrainingDataset:
    schema_version: str
    feature_manifest_version: str
    frequency: str
    generated_at: str
    period_start: str
    period_end: str
    regions: tuple[str, ...]
    feature_names: tuple[str, ...]
    rows: tuple[TrainingRow, ...]
    summary: Mapping[str, int]
    dataset_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", MappingProxyType(dict(self.summary)))


def build_training_dataset(
    observations: Iterable[HistoricalRiskPeriod],
    config: DatasetConfig | None = None,
) -> TrainingDataset:
    resolved = config or DatasetConfig()
    items = sorted(observations, key=lambda item: (item.region_id, item.as_of))
    if not items:
        raise DatasetValidationError("observations must not be empty")
    frequencies = {item.frequency for item in items}
    if len(frequencies) != 1:
        raise DatasetValidationError("all observations must use one frequency")
    frequency = next(iter(frequencies))
    keys = [(item.region_id, item.as_of) for item in items]
    if len(keys) != len(set(keys)):
        raise DatasetValidationError("duplicate region_id/as_of observation")

    rows: list[TrainingRow] = []
    by_region: dict[str, list[HistoricalRiskPeriod]] = {}
    for item in items:
        by_region.setdefault(item.region_id, []).append(item)
    for region_id in sorted(by_region):
        series = by_region[region_id]
        indexed = {_period_index(item.as_of, frequency): item for item in series}
        for current in series:
            current_index = _period_index(current.as_of, frequency)
            history = [indexed.get(current_index - lag) for lag in range(0, 6)]
            for horizon in sorted(resolved.horizons):
                future = indexed.get(current_index + horizon)
                features, reasons = _features(current, history, resolved.signal_names, frequency)
                target, target_reason = _target(future)
                rows.append(
                    TrainingRow(
                        region_id=region_id,
                        as_of=_iso(current.as_of),
                        horizon_periods=horizon,
                        horizon_days=horizon * 10 if frequency == "dekadal" else None,
                        target=target,
                        target_reason=target_reason,
                        target_as_of=_iso(future.as_of) if future is not None else None,
                        features=features,
                        feature_reasons=tuple(sorted(reasons)),
                        lineage={
                            "source_version": current.source_version,
                            "transformation_version": current.transformation_version,
                            "score_version": current.score_version,
                            "quality_flag": current.quality_flag,
                            "geometry_version": current.geometry_version,
                            "threshold_version": current.threshold_version,
                            "target_threshold_version": future.threshold_version if future else "",
                        },
                    )
                )

    feature_names = tuple(sorted(rows[0].features))
    summary_counter = Counter(
        f"h{row.horizon_periods}_target_{'null' if row.target is None else row.target}"
        for row in rows
    )
    summary_counter.update(
        {
            "row_count": len(rows),
            "region_count": len(by_region),
            "observation_count": len(items),
        }
    )
    base = {
        "schema_version": resolved.schema_version,
        "feature_manifest_version": resolved.feature_manifest_version,
        "frequency": frequency,
        "generated_at": _iso(max(item.as_of for item in items)),
        "period_start": _iso(min(item.as_of for item in items)),
        "period_end": _iso(max(item.as_of for item in items)),
        "regions": tuple(sorted(by_region)),
        "feature_names": feature_names,
        "rows": tuple(rows),
        "summary": dict(sorted(summary_counter.items())),
    }
    dataset_hash = hashlib.sha256(_canonical_json(base).encode("utf-8")).hexdigest()
    return TrainingDataset(**base, dataset_hash=f"sha256:{dataset_hash}")


def canonical_dataset_json(dataset: TrainingDataset) -> str:
    return _canonical_json(dataset) + "\n"


def write_training_dataset(dataset: TrainingDataset, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_dataset_json(dataset))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return target


def load_training_dataset(path: str | Path) -> TrainingDataset:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["regions"] = tuple(payload["regions"])
    payload["feature_names"] = tuple(payload["feature_names"])
    payload["rows"] = tuple(
        TrainingRow(
            **{
                **row,
                "feature_reasons": tuple(row["feature_reasons"]),
            }
        )
        for row in payload["rows"]
    )
    return TrainingDataset(**payload)


def _features(
    current: HistoricalRiskPeriod,
    history: list[HistoricalRiskPeriod | None],
    signal_names: tuple[str, ...],
    frequency: str,
) -> tuple[dict[str, float | None], set[str]]:
    features: dict[str, float | None] = {}
    reasons: set[str] = set()
    features["current_severe"] = (
        1.0
        if current.risk_level in {"orange", "red"}
        else 0.0
        if current.risk_level in {"green", "yellow"}
        else None
    )
    for name in signal_names:
        values = [item.signals.get(name) if item is not None else None for item in history]
        features[f"{name}_t"] = values[0]
        for lag in (1, 2, 3):
            features[f"{name}_lag_{lag}"] = values[lag]
            if history[lag] is None:
                reasons.add(f"{name}_lag_{lag}_gap")
        features[f"{name}_delta_1"] = _difference(values[0], values[1])
        features[f"{name}_rolling_mean_3"] = _mean_complete(values[:3])
        features[f"{name}_rolling_mean_6"] = _mean_complete(values[:6])
        features[f"{name}_slope_3"] = _slope(values[:3])
        features[f"{name}_recent_min_3"] = _extreme(values[:3], min)
        features[f"{name}_recent_max_3"] = _extreme(values[:3], max)
        observed_at = current.signal_observed_at.get(name)
        features[f"{name}_age_days"] = (
            (current.as_of - observed_at).total_seconds() / 86_400
            if observed_at is not None
            else None
        )
    rainfall_deficits = [
        max(0.0, -value) if value is not None else None
        for value in [
            item.signals.get("rainfall_anomaly") if item else None for item in history[:3]
        ]
    ]
    features["rainfall_deficit_rolling_sum_3"] = _sum_complete(rainfall_deficits)
    score_values = [item.signals.get("risk_score") if item else None for item in history]
    features["risk_deterioration_consecutive"] = float(_consecutive_deterioration(score_values))
    cycle_size = 12 if frequency == "monthly" else 36
    cycle_position = (
        current.as_of.month
        if frequency == "monthly"
        else ((current.as_of.month - 1) * 3 + _dekad(current.as_of))
    )
    features["season_sin"] = math.sin(2 * math.pi * cycle_position / cycle_size)
    features["season_cos"] = math.cos(2 * math.pi * cycle_position / cycle_size)
    if any(item is None for item in history[1:]):
        reasons.add("history_not_contiguous")
    return features, reasons


def _target(future: HistoricalRiskPeriod | None) -> tuple[int | None, str]:
    if future is None:
        return None, "future_period_missing"
    if future.quality_flag in BLOCKING_QUALITY:
        return None, "future_quality_blocked"
    if future.risk_level == "unknown":
        return None, "future_level_unknown"
    if future.risk_level in {"orange", "red"}:
        return 1, "conclusive"
    if future.risk_level in {"green", "yellow"}:
        return 0, "conclusive"
    return None, "future_level_invalid"


def _validate_observation(item: HistoricalRiskPeriod) -> None:
    required = {
        "region_id": item.region_id,
        "threshold_version": item.threshold_version,
        "source_version": item.source_version,
        "transformation_version": item.transformation_version,
        "score_version": item.score_version,
        "geometry_version": item.geometry_version,
    }
    missing = [name for name, value in required.items() if not value.strip()]
    if missing:
        raise DatasetValidationError(f"required values are empty: {', '.join(missing)}")
    if item.as_of.tzinfo is None or item.as_of.utcoffset() != timezone.utc.utcoffset(item.as_of):
        raise DatasetValidationError("as_of must be timezone-aware UTC")
    if item.frequency not in SUPPORTED_FREQUENCIES:
        raise DatasetValidationError("frequency must be monthly or dekadal")
    if item.risk_level not in KNOWN_LEVELS:
        raise DatasetValidationError("risk_level is invalid")
    for name, value in item.signals.items():
        if not name or not name.replace("_", "").isalnum():
            raise DatasetValidationError("signal names must use alphanumeric snake_case names")
        if value is not None and not math.isfinite(value):
            raise DatasetValidationError(f"signal {name} must be finite")
    unknown_dates = set(item.signal_observed_at) - set(item.signals)
    if unknown_dates:
        raise DatasetValidationError("signal_observed_at contains unknown signals")
    for name, observed_at in item.signal_observed_at.items():
        if observed_at.tzinfo is None or observed_at.utcoffset() != timezone.utc.utcoffset(
            observed_at
        ):
            raise DatasetValidationError(
                f"signal_observed_at for {name} must be timezone-aware UTC"
            )
        if observed_at > item.as_of:
            raise DatasetValidationError(f"signal_observed_at for {name} cannot be after as_of")


def _period_index(value: datetime, frequency: str) -> int:
    if frequency == "monthly":
        return value.year * 12 + value.month - 1
    return value.year * 36 + (value.month - 1) * 3 + _dekad(value) - 1


def _dekad(value: datetime) -> int:
    return 1 if value.day <= 10 else 2 if value.day <= 20 else 3


def _mean_complete(values: list[float | None]) -> float | None:
    return (
        sum(cast(list[float], values)) / len(values)
        if values and all(value is not None for value in values)
        else None
    )


def _sum_complete(values: list[float | None]) -> float | None:
    return (
        sum(cast(list[float], values))
        if values and all(value is not None for value in values)
        else None
    )


def _difference(left: float | None, right: float | None) -> float | None:
    return left - right if left is not None and right is not None else None


def _slope(values: list[float | None]) -> float | None:
    if len(values) != 3 or any(value is None for value in values):
        return None
    current, lag_1, lag_2 = values
    assert current is not None and lag_2 is not None
    return (current - lag_2) / 2.0


def _extreme(values: list[float | None], operation: Callable[[list[float]], float]) -> float | None:
    if not values or any(value is None for value in values):
        return None
    typed = [float(value) for value in values if value is not None]
    return operation(typed)


def _consecutive_deterioration(values: list[float | None]) -> int:
    count = 0
    for current, previous in zip(values, values[1:]):
        if current is None or previous is None or current <= previous:
            break
        count += 1
    return count


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> str:
    return json.dumps(
        _plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _plain(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value

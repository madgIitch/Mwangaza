from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from mwangaza.data.indicator_snapshot import IndicatorSnapshot


class DataQualityError(ValueError):
    pass


@dataclass(frozen=True)
class DataQualityRules:
    rules_version: str = "quality-v1"
    max_age_hours: int = 72
    critical_threshold: float = 50.0
    degraded_penalty: float = 15.0
    absent_penalty: float = 30.0


@dataclass(frozen=True)
class DataQualityReport:
    region_id: str
    period_start: str
    period_end: str
    score: float
    status: str
    blocks_automatic_alerts: bool
    contributions: dict[str, float]
    warnings: tuple[str, ...]
    rules_version: str
    available_indicators: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_data_quality(
    snapshot: IndicatorSnapshot,
    rules: DataQualityRules | None = None,
    *,
    now: datetime | None = None,
) -> DataQualityReport:
    resolved = rules or DataQualityRules()
    _validate_rules(resolved)
    current = now or datetime.now(UTC)
    newest = _parse_datetime(snapshot.newest_updated_at, "newest_updated_at")
    age_hours = max(0.0, (current - newest).total_seconds() / 3600)

    freshness = max(0.0, 100.0 - (age_hours / resolved.max_age_hours) * 100.0)
    spatial = _coverage_score(snapshot)
    temporal = 100.0 if snapshot.period_start <= snapshot.period_end else 0.0
    history = 100.0 if "insufficient_history" not in _quality_flags(snapshot) else 40.0

    raw_score = (freshness + spatial + temporal + history) / 4
    raw_score -= len(snapshot.indicators_degraded) * resolved.degraded_penalty
    raw_score -= len(snapshot.indicators_absent) * resolved.absent_penalty
    score = min(100.0, max(0.0, raw_score))

    warnings = _warnings(snapshot, age_hours, resolved)
    status = "data_review_required" if score < resolved.critical_threshold else "ok"
    if snapshot.indicators_degraded and status == "ok":
        status = "degraded"
    return DataQualityReport(
        region_id=snapshot.region_id,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        score=round(score, 3),
        status=status,
        blocks_automatic_alerts=status == "data_review_required",
        contributions={
            "freshness": round(freshness, 3),
            "spatial_coverage": round(spatial, 3),
            "temporal_coverage": round(temporal, 3),
            "history": round(history, 3),
        },
        warnings=warnings,
        rules_version=resolved.rules_version,
        available_indicators=snapshot.indicators_present + snapshot.indicators_degraded,
        metadata={"age_hours": round(age_hours, 3), "snapshot_id": snapshot.snapshot_id},
    )


def _coverage_score(snapshot: IndicatorSnapshot) -> float:
    coverages: list[float] = []
    for signal in snapshot.signals:
        metadata = signal.get("metadata", {})
        coverage = metadata.get("coverage_fraction")
        if coverage is None:
            continue
        if not isinstance(coverage, int | float) or not 0 <= coverage <= 1:
            raise DataQualityError("coverage_fraction must be inside [0, 1]")
        coverages.append(float(coverage) * 100)
    if not coverages:
        return 100.0 if not snapshot.indicators_absent else 50.0
    return sum(coverages) / len(coverages)


def _quality_flags(snapshot: IndicatorSnapshot) -> set[str]:
    return {str(signal.get("quality_flag")) for signal in snapshot.signals}


def _warnings(
    snapshot: IndicatorSnapshot,
    age_hours: float,
    rules: DataQualityRules,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if age_hours > rules.max_age_hours:
        warnings.append("stale_data")
    if snapshot.indicators_absent:
        warnings.append("missing_indicators")
    if snapshot.indicators_degraded:
        warnings.append("degraded_indicators")
    if "insufficient_history" in _quality_flags(snapshot):
        warnings.append("insufficient_history")
    return tuple(warnings)


def _validate_rules(rules: DataQualityRules) -> None:
    if not rules.rules_version:
        raise DataQualityError("rules_version is required")
    if rules.max_age_hours <= 0:
        raise DataQualityError("max_age_hours must be positive")
    if not 0 <= rules.critical_threshold <= 100:
        raise DataQualityError("critical_threshold must be inside [0, 100]")


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataQualityError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise DataQualityError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)


__all__ = [
    "DataQualityError",
    "DataQualityReport",
    "DataQualityRules",
    "evaluate_data_quality",
]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mwangaza.contracts import RiskSnapshot
from mwangaza.data.indicator_snapshot import IndicatorSnapshot
from mwangaza.quality import DataQualityReport


class RiskScoreError(ValueError):
    pass


@dataclass(frozen=True)
class RiskModelConfig:
    model_version: str = "composite-risk-v1"
    weights: dict[str, float] | None = None
    required_indicators: tuple[str, ...] = ("ndvi", "rainfall_mm")
    optional_indicators: tuple[str, ...] = ("lst_c",)

    def resolved_weights(self) -> dict[str, float]:
        return dict(self.weights or {"ndvi": 0.4, "rainfall_mm": 0.4, "lst_c": 0.2})


def compute_composite_drought_score(
    snapshot: IndicatorSnapshot,
    quality_report: DataQualityReport,
    config: RiskModelConfig | None = None,
) -> RiskSnapshot:
    resolved = config or RiskModelConfig()
    weights = resolved.resolved_weights()
    _validate_weights(weights)
    available = set(snapshot.indicators_present) | set(snapshot.indicators_degraded)
    missing_required = sorted(set(resolved.required_indicators) - available)
    if missing_required or quality_report.blocks_automatic_alerts:
        return _unknown_snapshot(snapshot, quality_report, resolved, missing_required)

    usable = sorted(available & set(weights))
    used_weights = _renormalize({indicator: weights[indicator] for indicator in usable})
    contributions: dict[str, dict[str, Any]] = {}
    score = 0.0
    signals = {signal["indicator"]: signal for signal in snapshot.signals}
    for indicator, weight in used_weights.items():
        value_score = _indicator_score(indicator, signals[indicator])
        weighted_contribution = value_score * weight
        score += weighted_contribution
        contributions[indicator] = {
            "weight": weight,
            "score": value_score,
            "weighted_contribution": round(weighted_contribution, 3),
            "source": signals[indicator].get("source"),
            "quality_flag": signals[indicator].get("quality_flag"),
        }
    score = round(min(100.0, max(0.0, score)), 3)
    return RiskSnapshot(
        region_id=snapshot.region_id,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        composite_score=score,
        risk_level=_risk_level(score),
        contributing_indicators=tuple(sorted(contributions)),
        source="mwangaza.risk.composite",
        quality_flag="degraded" if snapshot.indicators_degraded else "ok",
        is_simulated=snapshot.is_simulated,
        metadata={
            "model_version": resolved.model_version,
            "snapshot_id": snapshot.snapshot_id,
            "quality_score": quality_report.score,
            "contributions": contributions,
            "renormalized_weights": used_weights,
            "missing_optional": sorted(set(weights) - set(used_weights)),
        },
    )


def _unknown_snapshot(
    snapshot: IndicatorSnapshot,
    quality_report: DataQualityReport,
    config: RiskModelConfig,
    missing_required: list[str],
) -> RiskSnapshot:
    return RiskSnapshot(
        region_id=snapshot.region_id,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        composite_score=None,
        risk_level="low" if False else "low",
        contributing_indicators=(),
        source="mwangaza.risk.composite",
        quality_flag="invalid",
        is_simulated=snapshot.is_simulated,
        metadata={
            "model_version": config.model_version,
            "snapshot_id": snapshot.snapshot_id,
            "quality_score": quality_report.score,
            "risk_level_override": "unknown",
            "missing_required": missing_required,
            "blocked_by_quality": quality_report.blocks_automatic_alerts,
        },
    )


def _validate_weights(weights: dict[str, float]) -> None:
    if not weights:
        raise RiskScoreError("weights are required")
    total = sum(weights.values())
    if any(weight < 0 for weight in weights.values()):
        raise RiskScoreError("weights must be non-negative")
    if abs(total - 1.0) > 1e-9:
        raise RiskScoreError("weights must sum to 1")


def _renormalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise RiskScoreError("usable weights must be positive")
    return {indicator: weight / total for indicator, weight in sorted(weights.items())}


def _indicator_score(indicator: str, signal: dict[str, Any]) -> float:
    value = signal.get("value")
    metadata = signal.get("metadata", {})
    if value is None:
        value = metadata.get("percent_anomaly", metadata.get("absolute_anomaly_c", 0.0))
    numeric = float(value)
    if indicator == "ndvi":
        return max(0.0, min(100.0, (1.0 - numeric) * 100.0))
    if indicator == "rainfall_mm":
        return max(0.0, min(100.0, abs(numeric)))
    if indicator == "lst_c":
        return max(0.0, min(100.0, numeric + 50.0))
    return 0.0


def _risk_level(score: float) -> str:
    if score >= 75:
        return "emergency"
    if score >= 50:
        return "warning"
    if score >= 25:
        return "watch"
    return "low"


__all__ = ["RiskModelConfig", "RiskScoreError", "compute_composite_drought_score"]

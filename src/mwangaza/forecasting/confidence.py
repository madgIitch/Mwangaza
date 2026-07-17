from __future__ import annotations

from dataclasses import dataclass

from mwangaza.forecasting import BacktestResult, ForecastResult


@dataclass(frozen=True)
class ForecastIntervalPoint:
    step: int
    value: float
    lower: float
    upper: float


@dataclass(frozen=True)
class ForecastConfidenceResult:
    points: tuple[ForecastIntervalPoint, ...]
    confidence: float
    eligible: bool
    preventive_alert: bool
    reason: str
    diagnostic: str


def evaluate_forecast_confidence(
    forecast: ForecastResult,
    *,
    model_backtest: BacktestResult,
    naive_mae: float,
    current_observation: float,
    minimum_confidence: float = 0.6,
    drop_threshold: float = 0.05,
) -> ForecastConfidenceResult:
    if naive_mae <= 0:
        eligible = False
        confidence = 0.0
        reason = "rejected: invalid naive baseline"
    else:
        improvement = max(0.0, (naive_mae - model_backtest.mae) / naive_mae)
        confidence = min(1.0, improvement)
        eligible = model_backtest.mae < naive_mae and confidence >= minimum_confidence
        reason = "eligible: forecast improves baseline" if eligible else "rejected: confidence or baseline improvement too low"
    width = max(model_backtest.mae, 0.0)
    points = tuple(
        ForecastIntervalPoint(
            step=point.step,
            value=point.value,
            lower=point.value - width,
            upper=point.value + width,
        )
        for point in forecast.points
    )
    predicted_drop = bool(points and points[0].value <= current_observation - drop_threshold)
    preventive = eligible and predicted_drop
    if eligible and not predicted_drop:
        reason = "eligible diagnostics only: no configured forecast drop"
    return ForecastConfidenceResult(
        points=points,
        confidence=confidence,
        eligible=eligible,
        preventive_alert=preventive,
        reason=reason,
        diagnostic="Forecast is an experimental estimate, not an observed fact.",
    )


__all__ = ["ForecastConfidenceResult", "ForecastIntervalPoint", "evaluate_forecast_confidence"]

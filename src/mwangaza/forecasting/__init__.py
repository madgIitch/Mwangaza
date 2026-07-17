from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

MODEL_VERSION = "seasonal-baseline-v1"
MIN_POINTS = 4


@dataclass(frozen=True)
class ForecastPoint:
    step: int
    value: float


@dataclass(frozen=True)
class ForecastResult:
    region_id: str
    indicator: str
    trained_at: str
    horizon: int
    model_version: str
    points: tuple[ForecastPoint, ...]
    experimental: bool
    replaces_observation: bool


@dataclass(frozen=True)
class BacktestResult:
    mae: float
    safe_relative_error: float | None
    observations: int


class SeasonalBaselineModel:
    def __init__(self, *, model_version: str = MODEL_VERSION) -> None:
        self.model_version = model_version
        self._mean: float | None = None

    def fit(self, values: Iterable[float | None]) -> SeasonalBaselineModel:
        valid = _valid_values(values)
        if len(valid) < MIN_POINTS:
            raise ValueError("forecast requires at least four valid points")
        self._mean = sum(valid[-MIN_POINTS:]) / MIN_POINTS
        return self

    def predict(self, horizon: int) -> tuple[ForecastPoint, ...]:
        if self._mean is None:
            raise ValueError("model is not fitted")
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        return tuple(ForecastPoint(step=step, value=self._mean) for step in range(1, horizon + 1))


def fit_forecast(
    *,
    region_id: str,
    indicator: str,
    values: Iterable[float | None],
    horizon: int = 3,
    trained_at: datetime | None = None,
) -> ForecastResult:
    model = SeasonalBaselineModel().fit(values)
    ts = (trained_at or datetime.now(UTC)).replace(microsecond=0).isoformat()
    return ForecastResult(
        region_id=region_id,
        indicator=indicator,
        trained_at=ts,
        horizon=horizon,
        model_version=model.model_version,
        points=model.predict(horizon),
        experimental=True,
        replaces_observation=False,
    )


def backtest_forecast(values: Iterable[float | None]) -> BacktestResult:
    valid = _valid_values(values)
    if len(valid) < MIN_POINTS + 1:
        raise ValueError("backtest requires at least five valid points")
    errors: list[float] = []
    relatives: list[float] = []
    for index in range(MIN_POINTS, len(valid)):
        expected = sum(valid[index - MIN_POINTS : index]) / MIN_POINTS
        actual = valid[index]
        error = abs(actual - expected)
        errors.append(error)
        if actual != 0:
            relatives.append(error / abs(actual))
    return BacktestResult(
        mae=sum(errors) / len(errors),
        safe_relative_error=(sum(relatives) / len(relatives)) if relatives else None,
        observations=len(errors),
    )


def _valid_values(values: Iterable[float | None]) -> list[float]:
    return [float(value) for value in values if isinstance(value, int | float) and not isinstance(value, bool)]


__all__ = [
    "BacktestResult",
    "ForecastPoint",
    "ForecastResult",
    "MODEL_VERSION",
    "SeasonalBaselineModel",
    "backtest_forecast",
    "fit_forecast",
]

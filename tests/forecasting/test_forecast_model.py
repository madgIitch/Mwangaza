from __future__ import annotations

import unittest
from datetime import UTC, datetime

from mwangaza.forecasting import MODEL_VERSION, backtest_forecast, fit_forecast


class ForecastModelTests(unittest.TestCase):
    def test_default_model_is_deterministic_reproducible_and_metadata_rich(self) -> None:
        values = [0.2, 0.25, 0.3, 0.35, 0.4]
        trained_at = datetime(2026, 7, 17, 12, tzinfo=UTC)

        first = fit_forecast(region_id="som", indicator="ndvi", values=values, horizon=3, trained_at=trained_at)
        second = fit_forecast(region_id="som", indicator="ndvi", values=values, horizon=3, trained_at=trained_at)

        self.assertEqual(first, second)
        self.assertEqual(first.model_version, MODEL_VERSION)
        self.assertEqual(first.trained_at, "2026-07-17T12:00:00+00:00")
        self.assertEqual(first.horizon, 3)
        self.assertEqual(first.indicator, "ndvi")
        self.assertTrue(first.experimental)
        self.assertFalse(first.replaces_observation)
        self.assertEqual([point.step for point in first.points], [1, 2, 3])

    def test_does_not_train_without_minimum_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "four valid points"):
            fit_forecast(region_id="som", indicator="ndvi", values=[0.1, None, 0.2])

    def test_backtest_calculates_mae_and_safe_relative_error(self) -> None:
        result = backtest_forecast([0.0, 0.0, 0.0, 0.0, 0.2, 0.3])

        self.assertGreater(result.mae, 0)
        self.assertIsNotNone(result.safe_relative_error)
        self.assertEqual(result.observations, 2)

    def test_backtest_relative_error_is_none_when_actuals_are_zero(self) -> None:
        result = backtest_forecast([1.0, 1.0, 1.0, 1.0, 0.0])

        self.assertGreater(result.mae, 0)
        self.assertIsNone(result.safe_relative_error)


if __name__ == "__main__":
    unittest.main()

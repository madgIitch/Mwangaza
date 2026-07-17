from __future__ import annotations

import unittest
from datetime import UTC, datetime

from mwangaza.forecasting import BacktestResult, fit_forecast
from mwangaza.forecasting.confidence import evaluate_forecast_confidence
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import build_dashboard_shell_html


class ForecastConfidenceTests(unittest.TestCase):
    def test_forecast_points_include_lower_and_upper_interval(self) -> None:
        forecast = fit_forecast(
            region_id="som",
            indicator="ndvi",
            values=[0.3, 0.28, 0.24, 0.2],
            trained_at=datetime(2026, 7, 17, tzinfo=UTC),
        )

        result = evaluate_forecast_confidence(
            forecast,
            model_backtest=BacktestResult(mae=0.02, safe_relative_error=0.1, observations=5),
            naive_mae=0.1,
            current_observation=0.31,
        )

        self.assertTrue(result.eligible)
        self.assertTrue(result.preventive_alert)
        self.assertEqual(result.points[0].lower, result.points[0].value - 0.02)
        self.assertEqual(result.points[0].upper, result.points[0].value + 0.02)
        self.assertIn("eligible", result.reason)

    def test_model_must_beat_baseline_and_confidence_for_alert(self) -> None:
        forecast = fit_forecast(region_id="som", indicator="ndvi", values=[0.3, 0.28, 0.24, 0.2])

        result = evaluate_forecast_confidence(
            forecast,
            model_backtest=BacktestResult(mae=0.12, safe_relative_error=0.5, observations=5),
            naive_mae=0.1,
            current_observation=0.3,
        )

        self.assertFalse(result.eligible)
        self.assertFalse(result.preventive_alert)
        self.assertIn("rejected", result.reason)
        self.assertIn("experimental estimate", result.diagnostic)

    def test_no_drop_remains_diagnostic_without_preventive_alert(self) -> None:
        forecast = fit_forecast(region_id="som", indicator="ndvi", values=[0.3, 0.32, 0.34, 0.36])

        result = evaluate_forecast_confidence(
            forecast,
            model_backtest=BacktestResult(mae=0.01, safe_relative_error=0.05, observations=5),
            naive_mae=0.1,
            current_observation=0.3,
        )

        self.assertTrue(result.eligible)
        self.assertFalse(result.preventive_alert)
        self.assertIn("diagnostics", result.reason)

    def test_dashboard_labels_forecasts_as_estimates_not_facts(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Forecasts are experimental estimates", html)
        self.assertIn("not observed facts", html)


if __name__ == "__main__":
    unittest.main()

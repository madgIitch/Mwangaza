# Forecast Confidence

Sprint 37 adds confidence intervals and eligibility gates for experimental
forecasts.

Each evaluated forecast point includes lower and upper bounds based on backtest
MAE. A forecast is eligible only when it improves over a naive baseline and
meets the configured minimum confidence. Preventive alerts additionally require
a configured predicted drop.

Rejected models remain available as diagnostics with a persisted reason. The
dashboard labels forecasts as experimental estimates, not observed facts.

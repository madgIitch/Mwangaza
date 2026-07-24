# Forecast Confidence

Sprint 37 adds confidence intervals and eligibility gates for experimental
forecasts.

Each evaluated forecast point includes lower and upper bounds based on backtest
MAE. A forecast is eligible only when it improves over a naive baseline and
meets the configured minimum confidence. Preventive alerts additionally require
a configured predicted drop.

Rejected models remain available as diagnostics with a persisted reason. The
dashboard labels forecasts as experimental estimates, not observed facts.

Sprints 61-65 extend this abstention principle to calibrated probabilities: publication requires positive out-of-sample skill and approved quality, calibration, drift, horizon and regional-representation gates.

Sprint 62 implements the pre-calibration model-selection gate: logistic regression and histogram gradient boosting must improve persistence and seasonal climatology in globally dated, horizon-gapped walk-forward folds. Calibration and publication eligibility remain Sprint 63 responsibilities.

# Sprint 37 - Forecast Confidence

## Resultado

- Se agrego `forecasting.confidence` con intervalos, confianza, elegibilidad y preventive alert gate.
- Dashboard etiqueta forecasts como estimaciones experimentales, no hechos observados.

## Validaciones

- `uv run python -m unittest tests.forecasting.test_confidence`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-37-forecast-confidence`

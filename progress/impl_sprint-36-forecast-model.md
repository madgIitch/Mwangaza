# Sprint 36 - Forecast Model

## Resultado

- Se agrego `mwangaza.forecasting` con baseline determinista.
- Forecast experimental con fecha de entrenamiento, horizonte, version e indicador.
- Backtest con MAE y error relativo seguro.

## Validaciones

- `uv run python -m unittest tests.forecasting.test_forecast_model`
- `uv run python -m compileall -q src tests app.py`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-36-forecast-model`

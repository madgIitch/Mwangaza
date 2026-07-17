# Sesion actual

Feature: **sprint-37-forecast-confidence - Sprint 37 - Forecast Confidence** - estado: `review_pending`.

- agente: codex
- rama: `main`
- intentos: 1

## Siguiente accion

- Smoke visual: confirmar texto de forecast experimental en About. Cerrar con `node .harness/spec.mjs done sprint-37-forecast-confidence` si pasa.

## Ultimo resultado

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

Validaciones ejecutadas hasta ahora:

- `uv run python -m unittest tests.forecasting.test_confidence`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-37-forecast-confidence`

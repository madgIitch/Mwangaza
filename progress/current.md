# Sesion actual

Feature: **sprint-28-active-alerts - Sprint 28 - Active Alerts** - estado: `review_pending`.

- agente: codex
- rama: `main`
- intentos: 1

## Siguiente accion

- Smoke test humano en Streamlit: validar filtros de alertas activas, evidencia/accion principal y que el drilldown de region no re-renderiza la pagina principal. Cerrar con `node .harness/spec.mjs done sprint-28-active-alerts` si pasa.

## Ultimo resultado

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

Validaciones ejecutadas hasta ahora:

- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-28-active-alerts`

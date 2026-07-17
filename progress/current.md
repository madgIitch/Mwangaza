# Sesion actual

Feature: **sprint-25-subnational-pilot - Sprint 25 - Subnational Pilot** - estado: `review_pending`.

- agente: codex
- rama: `main`
- intentos: 1

## Siguiente accion

- Smoke test humano del dashboard live en Streamlit y cerrar con `node .harness/spec.mjs done sprint-25-subnational-pilot` si el drilldown subnacional responde correctamente.

## Ultimo resultado

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

Validaciones ejecutadas:

- `uv run python -m unittest tests.services.test_live_gee_dashboard tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-25-subnational-pilot`

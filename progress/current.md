# Sesion actual

Feature: **sprint-32-data-export - Sprint 32 - Data Export** - estado: `review_pending`.

- agente: codex
- rama: `main`
- intentos: 1

## Siguiente accion

- Smoke visual: confirmar que el panel de exportacion comunica snapshot visible, limite y geometria omitida. Cerrar con `node .harness/spec.mjs done sprint-32-data-export` si pasa.

## Ultimo resultado

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

Validaciones ejecutadas hasta ahora:

- `uv run python -m unittest tests.exports.test_visible_export`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-32-data-export`

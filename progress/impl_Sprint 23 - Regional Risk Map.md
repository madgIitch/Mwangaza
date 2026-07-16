# Implementacion - sprint-23-regional-risk-map - Sprint 23 - Regional Risk Map

## 2026-07-16T00:00:00Z - estado: review_pending

- agente: codex
- rama: `main`
- intentos: 1

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

## Notas

- Implementado manualmente siguiendo el spec aprobado.
- Anade `mwangaza.maps` con view model regional y render SVG/HTML determinista.
- Conecta el dashboard a snapshots de riesgo materializados en cache local; Streamlit no ejecuta Earth Engine.
- Regiones sin datos, score no finito o calidad bloqueante se muestran como `unknown`.
- Anade smoke manual `smoke_tests/sprint23_regional_risk_map_real_gee.py` para autenticar GEE y sembrar cache saneada.
- Verificacion ejecutada con `uv run python -m compileall -q src tests app.py smoke_tests`.
- Verificacion ejecutada con `uv run python -m unittest discover -s tests`.
- Diff-scope ejecutado con `node .harness/gates.mjs sprint-23-regional-risk-map`.

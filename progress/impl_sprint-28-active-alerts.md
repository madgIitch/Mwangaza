# Sprint 28 - Active Alerts

## Intento 1

Implementado por `codex`.

Cambios principales:

- El loader lee alertas activas desde SQLite con evidencia, recomendaciones, calidad, score, tipo de region y periodo.
- El panel lateral muestra la lista global de alertas activas priorizadas; el panel de region conserva el detalle filtrado por region.
- Las tarjetas incluyen evidencia resumida, accion principal sugerida y ranking de prioridad.
- La UI agrega filtros client-side por severidad, pais y tipo de region sin recalcular GEE ni reemplazar el shell de Streamlit.
- Las alertas resueltas quedan fuera de la lista activa por defecto y `unknown` se renderiza separado de `normal/green`.

Validaciones:

- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-28-active-alerts`

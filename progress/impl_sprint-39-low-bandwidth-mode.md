# Sprint 39 - Low-Bandwidth Mode

## Resultado

- Se agrego modo lite con `MWANGAZA_LOW_BANDWIDTH=1`.
- Lite omite SVG/geometria y renderiza tabla accesible con indicadores, alertas y acciones.
- Reportes, export y API siguen visibles.
- HTML lite es menor que modo completo en tests.

## Validaciones

- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m compileall -q src tests app.py`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-39-low-bandwidth-mode`

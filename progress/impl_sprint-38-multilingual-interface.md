# Sprint 38 - Multilingual Interface

## Resultado

- Se agrego `mwangaza.i18n` con catalogos `en`, `sw`, `so`, fallback y validacion.
- Dashboard traduce navegacion/modos y expone selector de idioma.
- Valores, fechas y fuentes permanecen sin traducir.

## Validaciones

- `uv run python -m unittest tests.i18n.test_i18n`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-38-multilingual-interface`

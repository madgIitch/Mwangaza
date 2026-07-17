# Sprint 29 - Historical Comparison

## Intento 1

Implementado por `codex`.

Cambios principales:

- Nuevo view model de comparacion historica por region, derivado de payloads ya cargados por live GEE/cache/demo.
- Comparacion limitada a periodos con la misma ventana estacional exacta por mes/dia.
- Exclusion de `no_data`, `insufficient_history` y valores no numericos.
- Panel `Historical Comparison` con versiones de datos, tabla de diferencias, narrativa cautelosa y ranking de sequedad por lluvia.
- Checkboxes client-side con limite de tres periodos historicos seleccionables.
- Actualizacion del panel al cambiar de region o periodo sin re-renderizar el shell.

Validaciones:

- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-29-historical-comparison`

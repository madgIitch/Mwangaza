# Sprint 32 - Data Export

## Resultado

- Se agrego `mwangaza.exports` con exportacion visible a CSV/JSON.
- JSON incluye `schema_version` y metadata de fuente; CSV comparte las mismas filas logicas.
- Geometria omitida por defecto, opcion simplificada explicita.
- Nulls se conservan como `null`/campo vacio y no como cero.
- Dashboard anuncia filenames CSV/JSON, limite de filas y geometria omitida.

## Validaciones

- `uv run python -m unittest tests.exports.test_visible_export`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-32-data-export`

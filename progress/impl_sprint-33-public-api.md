# Sprint 33 - Public API

## Resultado

- Se agregaron endpoints `/api/v1/regions`, `/api/v1/snapshots/latest`, `/api/v1/alerts`, `/api/v1/forecasts` y `/openapi.json`.
- Los endpoints v1 son de solo lectura y no llaman al loader live GEE.
- Listados con `limit`, `offset`, `total` y maximo 100.
- Errores saneados con `{error:{code,message}}`.

## Validaciones

- `uv run python -m unittest tests.api.test_public_api`
- `uv run python -m compileall -q src tests app.py`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-33-public-api`

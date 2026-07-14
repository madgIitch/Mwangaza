# Convenciones

- Metodología: SDD (una feature a la vez, spec aprobado antes de implementar).
- Sin ramas por feature: el harness trabaja en la rama actual y commitea cada feature ahí (`feat(<name>): <título>`). Para aislar una corrida entera, usa un `git worktree`.
- Una feature `sdd:true` queda en `review_pending` tras implementar; revisas el diff y la cierras con `spec.mjs done` (o `git revert` para descartarla).
- Tests obligatorios para cerrar una feature.

## Estilo de código

Lenguaje/framework principal: Python 3.11+, con dashboard Streamlit, API ASGI servible por Uvicorn y módulos de dominio bajo `src/mwangaza`.

Gestor de paquetes: `pip` con instalación editable desde `pyproject.toml`.

Comandos locales:

- Instalar: `python -m pip install -e .`
- Lint: `make lint` (equivalente Windows: `python -m compileall -q src tests app.py`)
- Typecheck/build: `make typecheck` (equivalente Windows: `python -m compileall -q src tests app.py`)
- Test: `make test` (equivalente Windows: `python -m unittest discover -s tests`)
- Dev server dashboard: `streamlit run app.py`
- Dev server API: `uvicorn mwangaza.api.app:app --reload`
- Refresh stub: `python -m mwangaza.data.refresh --dry-run`

Estructura relevante:

- `src/mwangaza/`: paquete importable y código de dominio.
- `src/mwangaza/api/`: entrypoint ASGI y contratos HTTP.
- `src/mwangaza/data/`: entrypoints de refresco y futuros adaptadores de datos.
- `src/mwangaza/ui/`: dashboard Streamlit.
- `tests/`: tests de contrato y regresión.

Reglas de diseño/API:

- Sprint 0 solo expone stubs seguros. No mostrar datos reales, simulados como producción ni claims operativos hasta que el spec correspondiente esté aprobado.
- Los contratos públicos mínimos son `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete `mwangaza`.

Reglas de tests:

- Los tests deben cubrir importabilidad, versión, entrypoints públicos y ausencia de llamadas remotas en stubs.

Reglas de despliegue:

- CI corre en Linux sobre `main` para push y pull request.

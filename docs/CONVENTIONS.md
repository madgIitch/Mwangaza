# Convenciones

- Metodologia: SDD (una feature a la vez, spec aprobado antes de implementar).
- Sin ramas por feature: el harness trabaja en la rama actual y commitea cada feature ahi (`feat(<name>): <titulo>`). Para aislar una corrida entera, usa un `git worktree`.
- Una feature `sdd:true` queda en `review_pending` tras implementar; revisas el diff y la cierras con `spec.mjs done` (o `git revert` para descartarla).
- Tests obligatorios para cerrar una feature.

## Estilo de codigo

Lenguaje/framework principal: Python 3.11+, con dashboard Streamlit, API ASGI servible por Uvicorn y modulos de dominio bajo `src/mwangaza`.

Gestor de paquetes: `pip` con instalacion editable desde `pyproject.toml`.

Comandos locales:

- Instalar: `python -m pip install -e .`
- Lint: `make lint` (en Windows resuelve Python desde `%LOCALAPPDATA%`; en Linux CI se invoca como `make PYTHON=python lint`)
- Typecheck/build: `make typecheck` (en Windows resuelve Python desde `%LOCALAPPDATA%`; en Linux CI se invoca como `make PYTHON=python typecheck`)
- Test: `make test` (en Windows resuelve Python desde `%LOCALAPPDATA%`; en Linux CI se invoca como `make PYTHON=python test`)
- Dev server dashboard: `streamlit run app.py`
- Dev server API: `uvicorn mwangaza.api.app:app --reload`
- Refresh stub: `python -m mwangaza.data.refresh --dry-run`

Estructura relevante:

- `src/mwangaza/`: paquete importable y codigo de dominio.
- `src/mwangaza/api/`: entrypoint ASGI y contratos HTTP.
- `src/mwangaza/data/`: entrypoints de refresco y futuros adaptadores de datos.
- `src/mwangaza/ui/`: dashboard Streamlit.
- `tests/`: tests de contrato y regresion.
- `smoke_tests/`: smoke tests manuales para integraciones prod-like con datos reales.

Reglas de diseno/API:

- Sprint 0 solo expone stubs seguros. No mostrar datos reales, simulados como produccion ni claims operativos hasta que el spec correspondiente este aprobado.
- Los contratos publicos minimos son `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete `mwangaza`.

Reglas de tests:

- Los tests deben cubrir importabilidad, version, entrypoints publicos y ausencia de llamadas remotas en stubs.
- Cuando una feature implemente o consuma datos externos reales (por ejemplo Earth Engine), el smoke test humano debe incluir una variante con datos reales y credenciales/configuracion de produccion o prod-like. Los tests automatizados siguen usando fakes/mocks para no depender de red ni secretos.
- Los smoke tests con datos reales no deben imprimir ni commitear secretos. Deben validar que los payloads saneados no contienen private keys, service accounts, client emails ni rutas locales sensibles.
- Los smoke tests con datos reales deben quedar versionados en `smoke_tests/` como scripts ejecutables/manuales. Para cada sprint aplicable, el agente debe generar o actualizar el script homologo sin esperar a que se pida explicitamente.
- Los scripts de `smoke_tests/` deben leer credenciales desde variables de entorno o rutas pasadas por variable, nunca desde una ruta local fija del desarrollador. Si falta configuracion, deben fallar con un mensaje accionable.

Reglas de despliegue:

- CI corre en Linux sobre `main` para push y pull request.

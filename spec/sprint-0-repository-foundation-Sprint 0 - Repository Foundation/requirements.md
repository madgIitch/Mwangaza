# sprint-0-repository-foundation · undefined — Requisitos

- name: `Sprint 0 - Repository Foundation` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T11:53:06.625Z

## Contexto



## Requisitos funcionales

R1. En un entorno limpio con Python 3.11, `python -m pip install -e .` instala el paquete sin errores y `python -c "import mwangaza; print(mwangaza.__version__)"` imprime `0.0.1`.
R2. `make lint`, `make typecheck` y `make test` existen, se ejecutan localmente y son los mismos comandos usados por CI; todos terminan con código 0.
R3. La CI ejecuta instalación editable, lint, typecheck y tests en cada push o pull request hacia `main`.
R4. `README.md` documenta comandos exactos para `streamlit run app.py`, levantar la API y ejecutar la actualización de datos, incluyendo comportamiento esperado sin credenciales reales.
R5. El código de dominio y los stubs de módulos viven bajo `src/mwangaza`; no se requiere ningún notebook para importar, ejecutar tests o arrancar entrypoints.
R6. `.env.example` contiene solo nombres de variables y valores placeholder no sensibles; no contiene claves, tokens, emails personales, rutas privadas ni identificadores de cuentas reales.
R7. El repositorio incluye `LICENSE` con licencia MIT y la versión declarada en metadata del paquete es `0.0.1`.

## Restricciones

- **error_states:** Los entrypoints iniciales deben arrancar sin credenciales ni datos reales en modo stub seguro, con un mensaje claro de que aun no hay integracion de datos. No deben fallar por falta de Earth Engine en Sprint 0 y no deben hacer fallback silencioso a datos simulados de produccion.
- **auth_secrets:** `.env.example` debe incluir solo placeholders no sensibles para perfil y rutas locales genericas: `MWANGAZA_ENV=local`, `MWANGAZA_LOG_LEVEL=INFO`, `MWANGAZA_DATA_DIR=./data`, `MWANGAZA_CACHE_DIR=./.cache/mwangaza`, `MWANGAZA_GEE_PROJECT=replace-me`, `MWANGAZA_GEE_SERVICE_ACCOUNT=replace-me`, `MWANGAZA_GEE_PRIVATE_KEY_JSON=replace-me`. La validacion completa de secretos queda para Sprint 1.
- **rollback_compat:** Sprint 0 fija como contratos publicos minimos los comandos `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete importable `mwangaza`. Cambios incompatibles posteriores deben registrarse en `docs/DECISIONS.md`.


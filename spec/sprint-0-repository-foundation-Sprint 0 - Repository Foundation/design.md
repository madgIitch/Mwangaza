# sprint-0-repository-foundation · undefined — Diseño

## Scope (archivos que puede tocar)

- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.github/workflows/**`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`
- `src/mwangaza/**`
- `tests/**`
- `app.py`
- `README.md`
- `LICENSE`

## Enfoque

- **data_model:** Sprint 0 queda limitado a estructura de modulos y stubs importables bajo `src/mwangaza`. No define contratos de dominio, modelos Pydantic, dataclasses ni schemas de indicadores, alertas o regiones; esos contratos empiezan en sprints posteriores. Los modulos pueden exponer funciones placeholder simples y documentadas solo para validar importabilidad.
- **external_contracts:** Quedan fijados los entrypoints exactos: dashboard `streamlit run app.py`, API `uvicorn mwangaza.api.app:app --reload` y refresco `python -m mwangaza.data.refresh --dry-run`. La API debe exponer al menos `/health` con estado stub, y el refresco dry-run debe imprimir que no consulta servicios remotos.
- **edge_cases:** Sprint 0 soporta Python 3.11+ y CI Linux. En Windows local se documentan comandos Python equivalentes; `make` es el contrato principal para CI y entornos Unix-like. Los entrypoints Python deben funcionar sin depender de notebooks ni datos locales.
- **ui_states:** `streamlit run app.py` debe mostrar una pantalla placeholder de producto con nombre, tagline, estado tecnico basico y aviso visible de `foundation stub`. No debe mostrar navegacion vacia ni claims de datos reales.

## Decisiones de la entrevista

- **adv-8b65469fd2:** La rama principal objetivo de CI es `main`; los triggers deben cubrir push y pull request hacia `main`.
- **adv-0c79bdd913:** Para Sprint 0 se usara licencia MIT como licencia publica compatible con la entrega.
- **data_model:** Sprint 0 debe crear solo la estructura de modulos y stubs importables. No debe definir contratos de dominio, modelos Pydantic, dataclasses ni schemas de indicadores/alertas/regiones; esos contratos empiezan en sprints posteriores. Cada modulo puede exponer funciones placeholder simples y documentadas para validar importabilidad.
- **error_states:** Los entrypoints iniciales deben arrancar sin credenciales ni datos reales en modo stub seguro, mostrando un mensaje claro de que aun no hay integracion de datos. No deben fallar por falta de Earth Engine en Sprint 0, y no deben hacer fallback silencioso a datos simulados de produccion.
- **edge_cases:** Sprint 0 soporta Python 3.11+ y CI Linux. En Windows local se documentan comandos Python equivalentes; `make` es el contrato principal para CI y entornos Unix-like, pero los entrypoints Python deben funcionar sin depender de notebooks.
- **auth_secrets:** `.env.example` debe incluir solo placeholders no sensibles para perfil y rutas locales genericas: `MWANGAZA_ENV=local`, `MWANGAZA_LOG_LEVEL=INFO`, `MWANGAZA_DATA_DIR=./data`, `MWANGAZA_CACHE_DIR=./.cache/mwangaza`, `MWANGAZA_GEE_PROJECT=replace-me`, `MWANGAZA_GEE_SERVICE_ACCOUNT=replace-me`, `MWANGAZA_GEE_PRIVATE_KEY_JSON=replace-me`. La validacion completa de secretos queda para Sprint 1.
- **external_contracts:** Documentar estos entrypoints exactos: dashboard `streamlit run app.py`; API `uvicorn mwangaza.api.app:app --reload`; refresco `python -m mwangaza.data.refresh --dry-run`. La API debe exponer al menos `/health` con estado stub, y el refresco dry-run debe imprimir que no consulta servicios remotos.
- **ui_states:** `streamlit run app.py` debe mostrar una pantalla placeholder de producto con nombre, tagline, estado tecnico basico y aviso visible de "foundation stub"; no debe mostrar navegacion vacia ni claims de datos reales.
- **rollback_compat:** Si. Sprint 0 fija como contratos publicos minimos los comandos `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete importable `mwangaza`. Cambios incompatibles posteriores deben registrarse en docs/DECISIONS.md.


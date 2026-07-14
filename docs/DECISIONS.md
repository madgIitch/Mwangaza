# Decisiones (ADR)

Formato por entrada: **fecha · título** — contexto, decisión y consecuencias.
El harness añade entradas cuando se aprueba un spec; el agente también debe añadir entradas cuando toma
una decisión de arquitectura relevante durante implementación.

## Pendientes de decisión

- (rellenar) Decisiones que aún no deben asumirse automáticamente.

<!-- Nuevas entradas debajo -->

<!-- harness:sprint-0-repository-foundation -->
## 2026-07-14 · sprint-0-repository-foundation aprobado

Contexto: se aprobó el spec `sprint-0-repository-foundation` (Sprint 0 - Repository Foundation).

Decisiones registradas:

- **auth_secrets:** `.env.example` debe incluir solo placeholders no sensibles para perfil y rutas locales genericas: `MWANGAZA_ENV=local`, `MWANGAZA_LOG_LEVEL=INFO`, `MWANGAZA_DATA_DIR=./data`, `MWANGAZA_CACHE_DIR=./.cache/mwangaza`, `MWANGAZA_GEE_PROJECT=replace-me`, `MWANGAZA_GEE_SERVICE_ACCOUNT=replace-me`, `MWANGAZA_GEE_PRIVATE_KEY_JSON=replace-me`. La validacion completa de secretos queda para Sprint 1.
- **rollback_compat:** Sprint 0 fija como contratos publicos minimos los comandos `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete importable `mwangaza`. Cambios incompatibles posteriores deben registrarse en `docs/DECISIONS.md`.
- **tests:** AC2 y CI cubren lint, typecheck y tests con codigo 0. Se refinan pruebas especificas para instalacion editable, importabilidad del paquete, version `0.0.1`, `/health`, entrypoints stub y refresco dry-run sin credenciales ni llamadas remotas.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

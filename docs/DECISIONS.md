# Decisiones (ADR)

Formato por entrada: **fecha · título** — contexto, decisión y consecuencias.
El harness añade entradas cuando se aprueba un spec; el agente también debe añadir entradas cuando toma
una decisión de arquitectura relevante durante implementación.

## Pendientes de decisión

- (rellenar) Decisiones que aún no deben asumirse automáticamente.

<!-- Nuevas entradas debajo -->

## 2026-07-15 · smoke tests con datos reales cuando aplique

Contexto: para validar que las integraciones satelitales funcionan fuera de fixtures locales, el smoke test humano debe parecerse a producción cuando el sprint toque datos externos reales.

Decisión: en los sprints que implementen o consuman datos externos reales, especialmente Earth Engine, el smoke test de cierre debe incluir una variante con datos reales y credenciales/configuración prod-like. Los tests automatizados continúan usando fakes/mocks para ser deterministas y no depender de red, cuota ni secretos.

Consecuencia: al entregar esos sprints, además de los tests unitarios, se debe proporcionar o ejecutar un smoke real que consulte la fuente externa, valide el contrato resultante y compruebe que no se filtran secretos en payloads, logs o salidas.

## 2026-07-15 · smoke tests reales versionados

Contexto: los smoke tests reales no deben depender de snippets pegados en el chat, porque los siguientes sprints necesitan una forma repetible y homogenea de validar integraciones externas.

Decisión: todo sprint que implemente o consuma datos externos reales debe incluir un script homologo en `smoke_tests/` cuando aplique. El agente debe crearlo o actualizarlo durante el sprint sin que el usuario lo pida explicitamente. Estos scripts deben usar variables de entorno para credenciales/rutas, no rutas locales fijas, y deben validar saneamiento de secretos en payloads.

Consecuencia: los cierres `review_pending` de sprints con datos reales deben apuntar a un smoke script versionado, además de los tests automatizados con fakes/mocks.

<!-- harness:sprint-0-repository-foundation -->
## 2026-07-14 · sprint-0-repository-foundation aprobado

Contexto: se aprobó el spec `sprint-0-repository-foundation` (Sprint 0 - Repository Foundation).

Decisiones registradas:

- **auth_secrets:** `.env.example` debe incluir solo placeholders no sensibles para perfil y rutas locales genericas: `MWANGAZA_ENV=local`, `MWANGAZA_LOG_LEVEL=INFO`, `MWANGAZA_DATA_DIR=./data`, `MWANGAZA_CACHE_DIR=./.cache/mwangaza`, `MWANGAZA_GEE_PROJECT=replace-me`, `MWANGAZA_GEE_SERVICE_ACCOUNT=replace-me`, `MWANGAZA_GEE_PRIVATE_KEY_JSON=replace-me`. La validacion completa de secretos queda para Sprint 1.
- **rollback_compat:** Sprint 0 fija como contratos publicos minimos los comandos `make lint`, `make typecheck`, `make test`, `streamlit run app.py`, `uvicorn mwangaza.api.app:app --reload`, `python -m mwangaza.data.refresh --dry-run` y el paquete importable `mwangaza`. Cambios incompatibles posteriores deben registrarse en `docs/DECISIONS.md`.
- **tests:** AC2 y CI cubren lint, typecheck y tests con codigo 0. Se refinan pruebas especificas para instalacion editable, importabilidad del paquete, version `0.0.1`, `/health`, entrypoints stub y refresco dry-run sin credenciales ni llamadas remotas.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-1-configuration-and-secrets -->
## 2026-07-14 · sprint-1-configuration-and-secrets aprobado

Contexto: se aprobó el spec `sprint-1-configuration-and-secrets` (Sprint 1 - Configuration and Secrets).

Decisiones registradas:

- **auth_secrets:** Variables privadas: `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PRIVATE_KEY_JSON`. En `production` son obligatorias junto con `MWANGAZA_GEE_PROJECT`. Variables publicas/no sensibles quedan enumeradas. En `local`, `test` y `demo` no se requieren credenciales reales.
- **rollback_compat:** Se mantienen como canonicos los nombres existentes de Sprint 0: `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PRIVATE_KEY_JSON`. `.env.example` debe actualizarse con nuevas variables publicas, secciones publica/privada y placeholders no sensibles. No hay renombres en Sprint 1.
- **tests:** Quedan especificados tests minimos para defaults locales, perfil test sin secretos, demo con fixtures, production incompleto, placeholders en production, fechas invertidas, pais invalido, sanitizacion en `repr(settings)`, `settings.to_public_dict()`, `/health` y logs, y compatibilidad con variables de Sprint 0.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-2-gee-authentication -->
## 2026-07-14 · sprint-2-gee-authentication aprobado

Contexto: se aprobó el spec `sprint-2-gee-authentication` (Sprint 2 - Google Earth Engine Authentication).

Decisiones registradas:

- **auth_secrets:** El secreto JSON se carga exclusivamente desde `MWANGAZA_GEE_PRIVATE_KEY_JSON` en memoria junto con `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PROJECT`. No se permite ruta ni archivo de secreto en ningun perfil. El adaptador no escribe secretos a disco ni registra valores. Login interactivo queda fuera de Sprint 2 y esta prohibido en production.
- **rollback_compat:** Se preservan invariantes de Sprint 1: nombres `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT`, `MWANGAZA_GEE_PRIVATE_KEY_JSON`; `/health` nunca filtra secretos; local/test/demo siguen ejecutandose sin credenciales reales; `Settings` y `public_config_status` conservan su contrato; refresh `--dry-run` sigue sin llamadas remotas. No se introducen rutas de secretos ni fallback silencioso de production a demo.
- **tests:** Tests unitarios con fakes para credenciales ausentes, JSON secreto en memoria, JSON invalido, SDK ausente, auth error, permission error, quota error, network timeout, exito, reintentos/backoff sin dormir y `/health` saneado. Ningun test importa ni llama Earth Engine real. La comprobacion manual vive en `docs/earth-engine.md` e indica variables, comando `python -m mwangaza.gee.auth --check`, resultado esperado y advertencia de no commitear secretos.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-3-igad-region-catalog -->
## 2026-07-14 · sprint-3-igad-region-catalog aprobado

Contexto: se aprobó el spec `sprint-3-igad-region-catalog` (Sprint 3 - IGAD Region Catalog).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-4-data-contracts -->
## 2026-07-14 · sprint-4-data-contracts aprobado

Contexto: se aprobó el spec `sprint-4-data-contracts` (Sprint 4 - Data Contracts).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-5-current-ndvi -->
## 2026-07-14 · sprint-5-current-ndvi aprobado

Contexto: se aprobó el spec `sprint-5-current-ndvi` (Sprint 5 - Current NDVI).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-6-ndvi-climatology -->
## 2026-07-14 · sprint-6-ndvi-climatology aprobado

Contexto: se aprobó el spec `sprint-6-ndvi-climatology` (Sprint 6 - NDVI Climatology).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-7-ndvi-anomaly -->
## 2026-07-14 · sprint-7-ndvi-anomaly aprobado

Contexto: se aprobó el spec `sprint-7-ndvi-anomaly` (Sprint 7 - NDVI Anomaly).

Decisiones registradas:

- **auth_secrets:** Sin secretos ni red.
- **rollback_compat:** Mantiene Sprints 0-6.
- **tests:** Cobertura de calculo, calidad, trazabilidad y validacion.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-8-current-rainfall -->
## 2026-07-14 · sprint-8-current-rainfall aprobado

Contexto: se aprobó el spec `sprint-8-current-rainfall` (Sprint 8 - Current Rainfall).

Decisiones registradas:

- **auth_secrets:** Sin secretos ni red.
- **rollback_compat:** Mantiene Sprints 0-7 y variables existentes.
- **tests:** Cobertura de calculo, calidad, config y no red.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-9-rainfall-climatology -->
## 2026-07-15 · sprint-9-rainfall-climatology aprobado

Contexto: se aprobó el spec `sprint-9-rainfall-climatology` (Sprint 9 - Rainfall Climatology).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-10-rainfall-anomaly -->
## 2026-07-15 · sprint-10-rainfall-anomaly aprobado

Contexto: se aprobó el spec `sprint-10-rainfall-anomaly` (Sprint 10 - Rainfall Anomaly).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-11-current-land-surface-temperature -->
## 2026-07-15 · sprint-11-current-land-surface-temperature aprobado

Contexto: se aprobó el spec `sprint-11-current-land-surface-temperature` (Sprint 11 - Current Land Surface Temperature).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-12-temperature-anomaly -->
## 2026-07-15 · sprint-12-temperature-anomaly aprobado

Contexto: se aprobó el spec `sprint-12-temperature-anomaly` (Sprint 12 - Temperature Anomaly).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-13-spatial-aggregation -->
## 2026-07-15 · sprint-13-spatial-aggregation aprobado

Contexto: se aprobó el spec `sprint-13-spatial-aggregation` (Sprint 13 - Spatial Aggregation).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-14-indicator-snapshot -->
## 2026-07-15 · sprint-14-indicator-snapshot aprobado

Contexto: se aprobó el spec `sprint-14-indicator-snapshot` (Sprint 14 - Indicator Snapshot).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-15-parquet-cache -->
## 2026-07-15 · sprint-15-parquet-cache aprobado

Contexto: se aprobó el spec `sprint-15-parquet-cache` (Sprint 15 - Parquet Cache).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-16-refresh-pipeline -->
## 2026-07-15 · sprint-16-refresh-pipeline aprobado

Contexto: se aprobó el spec `sprint-16-refresh-pipeline` (Sprint 16 - Refresh Pipeline).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-17-data-quality -->
## 2026-07-15 · sprint-17-data-quality aprobado

Contexto: se aprobó el spec `sprint-17-data-quality` (Sprint 17 - Data Quality).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-18-alert-thresholds -->
## 2026-07-15 · sprint-18-alert-thresholds aprobado

Contexto: se aprobó el spec `sprint-18-alert-thresholds` (Sprint 18 - Alert Thresholds).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-19-composite-drought-score -->
## 2026-07-15 · sprint-19-composite-drought-score aprobado

Contexto: se aprobó el spec `sprint-19-composite-drought-score` (Sprint 19 - Composite Drought Score).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

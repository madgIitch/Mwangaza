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

## 2026-07-21 · Atlas IGAD del Overview

Overview separa geometría y observación: carga de forma diferida los límites ADM1 locales versionados, los normaliza y consolida como una única geometría de presentación por país; después une score, severidad y calidad del snapshot por ID estable. El navegador no consulta GEE para navegar, hacer zoom, cambiar de capa o seleccionar un país. Los países ausentes o inválidos permanecen grises y el modo low-bandwidth no descarga el atlas SVG/GeoJSON.

## 2026-07-21 · ADM1 color keyed by stable boundary identity

Region Explorer uses geoBoundaries `shapeISO` as the presentation join key and exposes it as `boundary_iso` in the API. Names are labels only and national risk is never propagated to subdivisions. ADM1 GEE processing is bounded to the current period and configurable coverage; failures are isolated so an unavailable unit remains unassessed without collapsing the country payload.

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

<!-- harness:sprint-20-early-action-recommendations -->
## 2026-07-15 · sprint-20-early-action-recommendations aprobado

Contexto: se aprobó el spec `sprint-20-early-action-recommendations` (Sprint 20 - Early Action Recommendations).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-21-alert-persistence -->
## 2026-07-15 · sprint-21-alert-persistence aprobado

Contexto: se aprobó el spec `sprint-21-alert-persistence` (Sprint 21 - Alert Persistence).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-22-dashboard-shell -->
## 2026-07-15 · sprint-22-dashboard-shell aprobado

Contexto: se aprobó el spec `sprint-22-dashboard-shell` (Sprint 22 - Dashboard Shell).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-23-regional-risk-map -->
## 2026-07-16 · sprint-23-regional-risk-map aprobado

Contexto: se aprobó el spec `sprint-23-regional-risk-map` (Sprint 23 - Regional Risk Map).

Decisión: el dashboard debe consultar Google Earth Engine directamente en modo `live` cuando haya credenciales configuradas, usando solo region y periodo acotados por el sistema. Si GEE no esta disponible, debe caer a cache/demo con origen visible. El smoke real usa la misma ruta live y ademas siembra cache para validacion.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-24-country-drilldown -->
## 2026-07-16 · sprint-24-country-drilldown aprobado

Contexto: se aprobó el spec `sprint-24-country-drilldown` (Sprint 24 - Country Drilldown).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-25-subnational-pilot -->
## 2026-07-16 · sprint-25-subnational-pilot aprobado

Contexto: se aprobó el spec `sprint-25-subnational-pilot` (Sprint 25 - Subnational Pilot).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-26-temporal-slider -->
## 2026-07-17 · sprint-26-temporal-slider aprobado

Contexto: se aprobó el spec `sprint-26-temporal-slider` (Sprint 26 - Temporal Slider).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-27-indicator-trends -->
## 2026-07-17 · sprint-27-indicator-trends aprobado

Contexto: se aprobó el spec `sprint-27-indicator-trends` (Sprint 27 - Indicator Trends).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-28-active-alerts -->
## 2026-07-17 · sprint-28-active-alerts aprobado

Contexto: se aprobó el spec `sprint-28-active-alerts` (Sprint 28 - Active Alerts).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-29-historical-comparison -->
## 2026-07-17 · sprint-29-historical-comparison aprobado

Contexto: se aprobó el spec `sprint-29-historical-comparison` (Sprint 29 - Historical Comparison).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-30-exposure-estimation -->
## 2026-07-17 · sprint-30-exposure-estimation aprobado

Contexto: se aprobó el spec `sprint-30-exposure-estimation` (Sprint 30 - Exposure Estimation).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-31-executive-pdf-report -->
## 2026-07-17 · sprint-31-executive-pdf-report aprobado

Contexto: se aprobó el spec `sprint-31-executive-pdf-report` (Sprint 31 - Executive PDF Report).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-32-data-export -->
## 2026-07-17 · sprint-32-data-export aprobado

Contexto: se aprobó el spec `sprint-32-data-export` (Sprint 32 - Data Export).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-33-public-api -->
## 2026-07-17 · sprint-33-public-api aprobado

Contexto: se aprobó el spec `sprint-33-public-api` (Sprint 33 - Public API).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-34-audit-trail -->
## 2026-07-17 · sprint-34-audit-trail aprobado

Contexto: se aprobó el spec `sprint-34-audit-trail` (Sprint 34 - Audit Trail).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-35-notification-simulator -->
## 2026-07-17 · sprint-35-notification-simulator aprobado

Contexto: se aprobó el spec `sprint-35-notification-simulator` (Sprint 35 - Notification Simulator).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-36-forecast-model -->
## 2026-07-17 · sprint-36-forecast-model aprobado

Contexto: se aprobó el spec `sprint-36-forecast-model` (Sprint 36 - Forecast Model).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-37-forecast-confidence -->
## 2026-07-17 · sprint-37-forecast-confidence aprobado

Contexto: se aprobó el spec `sprint-37-forecast-confidence` (Sprint 37 - Forecast Confidence).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-38-multilingual-interface -->
## 2026-07-17 · sprint-38-multilingual-interface aprobado

Contexto: se aprobó el spec `sprint-38-multilingual-interface` (Sprint 38 - Multilingual Interface).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-39-low-bandwidth-mode -->
## 2026-07-17 · sprint-39-low-bandwidth-mode aprobado

Contexto: se aprobó el spec `sprint-39-low-bandwidth-mode` (Sprint 39 - Low-Bandwidth Mode).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-40-pwa-installability -->
## 2026-07-17 · sprint-40-pwa-installability aprobado

Contexto: se aprobó el spec `sprint-40-pwa-installability` (Sprint 40 - React PWA Migration).

Decisiones registradas:

- **auth_secrets:** Sin secretos ni GEE directo en navegador.
- **rollback_compat:** `app.py` queda como shim documentado.
- **tests:** Cobertura frontend y gates JS definidos.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-41-admin-configuration -->
## 2026-07-17 · sprint-41-admin-configuration aprobado

Contexto: se aprobó el spec `sprint-41-admin-configuration` (Sprint 41 - Admin Configuration).

Decisiones registradas:

- **auth_secrets:** El panel de hackathon es público y no usa credenciales; producción requerirá autenticación y autorización institucional.
- **rollback_compat:** Defaults existentes se conservan.
- **tests:** Cobertura API y frontend definida.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-42-observability -->
## 2026-07-18 · sprint-42-observability aprobado

Contexto: se aprobó el spec `sprint-42-observability` (Sprint 42 - Observability).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-43-security-and-privacy -->
## 2026-07-18 · sprint-43-security-and-privacy aprobado

Contexto: se aprobó el spec `sprint-43-security-and-privacy` (Sprint 43 - Security and Privacy).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-44-automated-testing -->
## 2026-07-18 · sprint-44-automated-testing aprobado

Contexto: se aprobó el spec `sprint-44-automated-testing` (Sprint 44 - Automated Testing).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-45-somalia-end-to-end-scenario -->
## 2026-07-20 · sprint-45-somalia-end-to-end-scenario aprobado

Contexto: se aprobó el spec `sprint-45-somalia-end-to-end-scenario` (Sprint 45 - Somalia End-to-End Scenario).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-46-northern-kenya-end-to-end-scenario -->
## 2026-07-20 · sprint-46-northern-kenya-end-to-end-scenario aprobado

Contexto: se aprobó el spec `sprint-46-northern-kenya-end-to-end-scenario` (Sprint 46 - Northern Kenya End-to-End Scenario).

Decisiones registradas:

- **auth_secrets:** El flujo sigue siendo completamente offline/demo: no realiza red, no inicializa GEE ni requiere credenciales externas. Los artefactos derivados deben quedar marcados como `demo` o `simulated`.
- **rollback_compat:** Sprint 46 es estrictamente aditivo. Debe preservar el escenario Somalia y los contratos actuales de `/region`, `/reports` y notificaciones simuladas. Los campos específicos de Kenya solo pueden añadirse como opcionales o encapsulados en fixture/estado demo, sin convertirlos en requisitos obligatorios de contratos existentes.
- **tests:** La cobertura mínima incluye: E2E offline del script; prueba de selección desde mapa y tabla accesible; correspondencia entre unidad activa y reporte; notificación en `en`, `sw` y `so` con fallback a inglés cuando falte plantilla; empate determinista; errores por fixture corrupto/ausente y reporte obligatorio ausente; verificación de ausencia de red y credenciales; e idempotencia sin duplicar alertas ni notificaciones.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-47-offline-demo-fallback -->
## 2026-07-20 · sprint-47-offline-demo-fallback aprobado

Contexto: se aprobó el spec `sprint-47-offline-demo-fallback` (Sprint 47 - Offline Demo Fallback).

Decisiones registradas:

- **auth_secrets:** Se mantiene que `demo` arranca sin `MWANGAZA_GEE_*`, sin red y sin servicios remotos. En `production`, la ausencia de credenciales deriva únicamente en `cache` explícita o error estructurado, nunca en `demo`.
- **rollback_compat:** Se preservan sin ruptura los endpoints y el shape base de `/region` y `/reports`, los `snapshot_id` de Somalia y Northern Kenya, y los IDs estables de alertas y outbox. Los cambios de payload solo pueden ser aditivos. El modo conectado y el modo `cache` existentes conservan su comportamiento actual.
- **tests:** La matriz mínima bloqueante queda fijada: arranque demo sin secretos; ausencia de red e inicialización GEE en demo; banner persistente en todas las rutas aprobadas, incluidos errores; reset idempotente y aislamiento de estado no demo; escenarios Somalia y Kenya offline; reports/export demo; compatibilidad de contratos; y caso negativo de `production` sin credenciales verificando `cache` explícita o error, nunca `demo`.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-48-data-provenance-documentation -->
## 2026-07-20 · sprint-48-data-provenance-documentation aprobado

Contexto: se aprobó el spec `sprint-48-data-provenance-documentation` (Sprint 48 - Data Provenance Documentation).

Decisiones registradas:

- **auth_secrets:** La feature sigue siendo documental y no introduce manejo nuevo de credenciales. La documentación puede nombrar plataformas y datasets, pero no debe exponer secretos, identificadores sensibles ni valores internos de configuración.
- **rollback_compat:** El cambio sigue siendo aditivo: añade documentación, navegación y catálogo canónico sin romper contratos existentes, siempre que `/about` mantenga sus rutas actuales y el nuevo enlace complemente, no sustituya, la navegación ya existente.
- **tests:** Los tests deben verificar como mínimo: existencia y navegación de `/about/provenance`; presencia del enlace `Data provenance and methodology` en `/about`; renderizado de al menos un encabezado único de la documentación; presencia de las entradas mínimas MODIS NDVI, CHIRPS rainfall, MODIS LST, límites administrativos y exposición poblacional; completitud de campos obligatorios del catálogo; definiciones separadas de `observation`, `anomaly`, `score`, `forecast` y `exposure`; aviso visible de que los thresholds son configurables y no oficiales; y un esquema/cadena inequívoca `source -> transformation -> cache -> API -> UI -> report`.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-49-public-readme -->
## 2026-07-20 · sprint-49-public-readme aprobado

Contexto: se aprobó el spec `sprint-49-public-readme` (Sprint 49 - Public README).

Decisiones registradas:

- **auth_secrets:** La sección pública solo puede listar nombres de variables y prerequisitos públicos. No debe incluir valores, claves, blobs JSON ni tutoriales de creación de credenciales; cualquier detalle sensible se deriva a `docs/configuration.md` y `docs/security/**`.
- **rollback_compat:** Se permite reestructurar completamente el README actual porque está obsoleto, pero deben conservarse anchors públicos razonables para `Requirements`, `Installation`, `Architecture`, `Testing`, `Configuration`, `Limitations` y `Roadmap`. También debe evitarse romper expectativas de onboarding ya trazadas desde CI, `docs/` o revisiones versionadas.
- **tests:** La verificación mínima queda cerrada: cada comando publicado en el README debe estar cubierto por CI o por una verificación manual reproducible versionada en `progress/review_sprint-49-public-readme.md`. Los comandos de calidad deben mapearse a CI o al smoke versionado del Sprint 49; los arranques y escenarios pueden validarse manualmente si la evidencia queda documentada.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-50-landing-page -->
## 2026-07-20 · sprint-50-landing-page aprobado

Contexto: se aprobó el spec `sprint-50-landing-page` (Sprint 50 - Landing Page).

Decisiones registradas:

- **auth_secrets:** La landing es pública, no depende de Earth Engine y no requiere credenciales `MWANGAZA_GEE_*`. La configuración de enlaces usa solo valores públicos no sensibles definidos en código versionado.
- **rollback_compat:** La feature es estrictamente aditiva: deben preservarse intactos `/`, `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin`, `/technical`, el banner demo y los contratos existentes. Solo se añade `/landing` junto con sus assets y configuración pública.
- **tests:** Quedan como mínimos bloqueantes: smoke de contenido visible con exactamente tres capacidades; verificación de URLs configuradas y omisión de CTAs inválidos; prueba de que `/landing` es aditiva y no altera rutas existentes; comprobación CSS/DOM a 320 px sin overflow horizontal; ausencia de inicialización o llamadas remotas/GEE; y prueba que rechaza claims cuantitativos sin cita visible o referencia explícita aprobada.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-56-region-explorer-completion -->
## 2026-07-20 · sprint-56-region-explorer-completion aprobado

Contexto: se aprobó el spec `sprint-56-region-explorer-completion` (Sprint 56 - Region Explorer Completion).

Decisiones registradas:

- **auth_secrets:** Sin secretos ni GEE desde el navegador; demo local.
- **rollback_compat:** Rutas y contratos previos preservados.
- **tests:** Matriz bloqueante demo/live y smoke real GEE definida.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

## 2026-07-21 · Cobertura ADM1 completa en GEE

La cobertura live por defecto incluye las 121 unidades ADM1 de los ocho países IGAD habilitados y se resuelve en un único lote para el periodo actual. Para ADM1, MOD13Q1 admite `SummaryQA` 0 y 1; el valor 1 está documentado por el proveedor como marginal pero útil y queda declarado en metadatos. No se aceptan valores 2-3 ni se propagan scores nacionales a unidades sin observación.

## 2026-07-21 · Espacio de trabajo cartográfico en Region Explorer

El panel `Why this region is at risk` funciona como contabilidad verificable del score, no como una visualización fija de pesos. Cada segmento representa puntos efectivos (`score normalizado × peso efectivo`) y muestra fuente y calidad. Las unidades ADM1 publican su propio desglose de forma aditiva; si falta, la interfaz declara el payload pendiente y nunca reutiliza el desglose nacional.

La lectura live de la API adopta stale-while-revalidate: sirve inmediatamente el último lote materializado, ejecuta un único refresh GEE en segundo plano y persiste atómicamente solo resultados con riesgo seleccionado utilizable. Las rutas auxiliares no esperan a GEE y la PWA consulta de nuevo mientras el modo sea `cache`. Un corte parcial más reciente permanece disponible en el selector, pero no desplaza como vista inicial al último corte válido de la región preferida.

La página regional adopta un atlas operacional centrado en el mapa. Mapa, selector ADM1 y ranking comparten una sola selección, y el detalle se concentra en un inspector lateral con score, severidad, indicadores, calidad, periodo, procedencia y acción contextual. El ranking queda plegado por defecto y con scroll interno para que su volumen no determine la composición de la página.

La selección trabaja exclusivamente con el payload ya cargado: el navegador no inicia consultas GEE adicionales. Las tendencias e históricos que siguen siendo nacionales se etiquetan con su alcance cuando hay un ADM1 activo. En low-bandwidth se mantiene la selección y evidencia equivalente mediante tablas, sin cargar el SVG administrativo.

La codificación visual separa magnitudes de estados: la severidad conserva los colores del mapa y badges, mientras las contribuciones efectivas del composite usan una barra apilada azul-gris. Las tendencias se representan como anomalía `value - baseline` alrededor de cero, con escala y fechas. Los deltas históricos indican dirección sin atribuir por color que subir o bajar sea siempre favorable. Solo se muestra una acción principal: primero el alert regional activo de mayor severidad y, si no existe, la primera recomendación; el horizonte temporal queda pendiente de un contrato estructurado.

Las tendencias live se materializan como 24 agregados mensuales nacionales por defecto, configurables entre 12 y 24. Ventanas y países se resuelven en un único grafo/request GEE y no se replican por ADM1. Son payloads exclusivos de serie: no contaminan el selector de periodos ni la comparación estacional. Si la fuente no aporta baseline, el shell usa la media de valores mensuales disponibles y lo declara explícitamente; nunca la denomina climatología oficial.

El fallback del grafo regional conserva la misma cobertura funcional: si el lote conjunto falla, se reintenta cada país habilitado de forma independiente. Un fallo nacional se registra y se aísla sin limitar las series restantes a Somalia o a la región inicialmente seleccionada.

<!-- harness:sprint-57-overview-completion -->
## 2026-07-21 · sprint-57-overview-completion aprobado

Contexto: se aprobó el spec `sprint-57-overview-completion` (Sprint 57 - Overview Completion).

Decisiones registradas:

- **auth_secrets:** Archivos desde snapshots; sin input ni secretos GEE.
- **rollback_compat:** Rutas previas preservadas y Reports Center fuera de alcance.
- **tests:** Matriz API/PWA, demo/live y ausencia de consultas GEE definida.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-58-alerts-center-completion -->
## 2026-07-21 · sprint-58-alerts-center-completion aprobado

Contexto: se aprobó el spec `sprint-58-alerts-center-completion` (Sprint 58 - Alerts Center Completion).

Decisiones registradas:

- **auth_secrets:** lectura segura; sin settings ni envío real.
- **rollback_compat:** rutas/campos actuales preservados.
- **tests:** API, persistencia, export y PWA cubiertos.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-59-reports-center-completion -->
## 2026-07-22 · sprint-59-reports-center-completion aprobado

Contexto: se aprobó el spec `sprint-59-reports-center-completion` (Sprint 59 - Reports Center Completion).

Decisiones registradas:

- **auth_secrets:** `/reports` es público y de sólo lectura. Generar y descargar PDF/CSV/JSON usa exclusivamente datos ya materializados y no requiere secretos del navegador. Programación, gestión de plantillas, compartir y distribución quedan deshabilitados hasta disponer de autenticación, roles y permisos aprobados. No se simula persistencia ni envío real y no se exponen destinatarios o secretos.
- **rollback_compat:** La experiencia es aditiva y preserva `/reports`, deep-links existentes, contratos de exports y reportes previos, demo determinista y funcionamiento offline. Payloads antiguos pueden mostrarse con degradación explícita, pero nunca se inventan IDs/timestamps. Si el historial no está disponible, generación y descargas actuales siguen operativas. No se añade feature flag; el rollback es revertir el commit del sprint.
- **tests:** Los tests bloqueantes deben cubrir contratos y estabilidad de IDs/timestamps, estados de lifecycle, filtros combinados, orden/selección, generación y descarga real de PDF/CSV/JSON, archivos no vacíos y cabeceras seguras, preview HTML/PDF correctamente etiquetado, deep-links, low-bandwidth, errores independientes, funciones `pending_contract`, auditoría permitida, ausencia de GEE y envíos reales desde navegador, demo offline y documentación de implementado/pendiente/futuro.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-60-about-methodology-completion -->
## 2026-07-23 · sprint-60-about-methodology-completion aprobado

Contexto: se aprobó el spec `sprint-60-about-methodology-completion` (Sprint 60 - About and Methodology Completion).

Decisiones registradas:

- **auth_secrets:** Todas las superficies son públicas, de sólo lectura y saneadas.
- **rollback_compat:** Se preservan rutas, demo y contratos existentes.
- **tests:** Contratos, UI, seguridad, offline y accesibilidad quedan cubiertos.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-61-probabilistic-training-dataset -->
## 2026-07-23 · sprint-61-probabilistic-training-dataset aprobado

Contexto: se aprobó el spec `sprint-61-probabilistic-training-dataset` (Sprint 61 - Probabilistic Training Dataset).

Decisiones registradas:

- **auth_secrets:** Offline y metadata saneada.
- **rollback_compat:** Implementación aditiva.
- **tests:** Matriz anti-leakage y reproducibilidad definida.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-62-calibrated-risk-classifier -->
## 2026-07-24 · sprint-62-calibrated-risk-classifier aprobado

Contexto: se aprobó el spec `sprint-62-calibrated-risk-classifier` (Sprint 62 - Calibrated Risk Classifier).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

<!-- harness:sprint-62b-real-historical-backfill -->
## 2026-07-24 · sprint-62b-real-historical-backfill aprobado

Contexto: se aprobó el spec `sprint-62b-real-historical-backfill` (Sprint 62B - Real Historical Backfill).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.
## 2026-07-24 · Real historical data uses native source cadence

The probabilistic backfill stores one regional row per calendar dekad, but it does not pretend that every signal is observed dekadally. CHIRPS Daily is accumulated within the period; MOD13Q1 and MOD11A2 retain the timestamp of the latest non-future composite and expose its age. Empty or not-yet-published upstream periods remain null with a reason code. Source rasters and downloaded local aggregates are not committed to Git.
## 2026-07-24 · Probabilistic thresholds are frozen from the pre-2024 baseline

Absolute 25/50/75 cuts produced no severe labels because the anomaly composite observed maximum was below 50. Threshold v2 uses country-level P75/P90/P97.5 calculated only from valid 2003-2023 baseline scores. The cuts are persisted before labeling current history, preventing 2024+ observations from tuning their own target. Model selection must improve persistence, seasonal climatology and historical frequency; otherwise Mwangaza abstains.

Threshold v3 strengthens temporal separation: `2003-2017` fits climatology and country thresholds, while only `2018-2026` is labeled for modeling. This yields 86 severe targets per horizon without allowing labeled dates to influence their own cuts. The expanded run still loses to historical frequency and therefore remains in abstention.

## 2026-07-25 · ADM1 antecedents separate observations, provider indices and forecasts

The next predictive dataset uses all 121 version-pinned IGAD ADM1 units. Raw source values and derived antecedents are separate artifacts: SPEIbase remains a provider-standardized monthly signal, while Mwangaza computes empirical SPI 1/3/6 from complete CHIRPS months using only the pre-cut reference distribution. Rainfall deficits and NDVI persistence/velocity likewise require contiguous completed windows.

FLDAS soil moisture remains a volume fraction and `Evap_tavg` remains a rate in `kg/m²/s`; neither is silently converted. MOD13Q1 is filtered by the end of its 16-day composite rather than only its start timestamp. ECMWF cumulative precipitation is converted from metres to millimetres but retains creation time and 240/360-hour lead. It is structurally unavailable before 2024-11-12 and never has an observation timestamp. A dekad becomes available at the start of the day after its final included daily observation.

<!-- harness:sprint-62c-adm1-antecedent-signals -->
## 2026-07-25 · sprint-62c-adm1-antecedent-signals aprobado

Contexto: se aprobó el spec `sprint-62c-adm1-antecedent-signals` (Sprint 62C - ADM1 Antecedent Drought Signals).

Decisión: implementar según el spec aprobado.

Consecuencia: futuras features deben respetar este contrato salvo nuevo ADR.

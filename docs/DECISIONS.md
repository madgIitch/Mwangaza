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

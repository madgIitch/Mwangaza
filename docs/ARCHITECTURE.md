# Arquitectura

> El agente lo lee antes de implementar. Mantén aquí el contexto que no cabe en una feature concreta.

## Visión general

Producto/proyecto:

Usuarios principales:

Objetivo no negociable:

## Componentes

- (rellenar) Componente:
  - Responsabilidad:
  - Entradas/salidas:
  - Dueño/riesgo:

## Flujo de datos

1. (rellenar)

## Integraciones externas

- (rellenar) Servicio/API:
  - Contrato:
  - Credenciales/config:
  - Entorno local/CI:

## Restricciones conocidas

- (rellenar) Rendimiento, seguridad, compatibilidad, despliegue, coste, etc.

## Decisiones abiertas

- (rellenar) Preguntas que bloquean diseño futuro.

<!-- Los specs aprobados se anexan debajo con marcadores harness:<id>. -->

<!-- harness:sprint-0-repository-foundation -->
## sprint-0-repository-foundation · Sprint 0 - Repository Foundation



### Scope aprobado

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

### Contexto técnico

- **data_model:** Sprint 0 queda limitado a estructura de modulos y stubs importables bajo `src/mwangaza`. No define contratos de dominio, modelos Pydantic, dataclasses ni schemas de indicadores, alertas o regiones; esos contratos empiezan en sprints posteriores. Los modulos pueden exponer funciones placeholder simples y documentadas solo para validar importabilidad.
- **external_contracts:** Quedan fijados los entrypoints exactos: dashboard `streamlit run app.py`, API `uvicorn mwangaza.api.app:app --reload` y refresco `python -m mwangaza.data.refresh --dry-run`. La API debe exponer al menos `/health` con estado stub, y el refresco dry-run debe imprimir que no consulta servicios remotos.
- **edge_cases:** Sprint 0 soporta Python 3.11+ y CI Linux. En Windows local se documentan comandos Python equivalentes; `make` es el contrato principal para CI y entornos Unix-like. Los entrypoints Python deben funcionar sin depender de notebooks ni datos locales.
- **ui_states:** `streamlit run app.py` debe mostrar una pantalla placeholder de producto con nombre, tagline, estado tecnico basico y aviso visible de `foundation stub`. No debe mostrar navegacion vacia ni claims de datos reales.

<!-- harness:sprint-1-configuration-and-secrets -->
## sprint-1-configuration-and-secrets · Sprint 1 - Configuration and Secrets



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/api/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/ui/**`
  - `tests/**`
  - `.env.example`
  - `README.md`
  - `docs/**`
  - `spec/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Define `Settings` como dataclass inmutable en `src/mwangaza/config.py`, construido por `load_settings(env: Mapping[str, str] | None = None)`, sin Pydantic. Campos, tipos, defaults y perfiles validos quedan especificados: `environment`, `log_level`, rutas, paises habilitados, periodo de climatologia, credenciales GEE opcionales y `max_remote_pixels`.
- **external_contracts:** Todos los entrypoints publicos cargan `Settings`: API `/health`, dashboard y refresh. `/health` expone solo campos saneados: `environment`, `version`, `status`, `config_valid`, `enabled_countries`, `climatology_period` y nombres de variables faltantes, sin valores. Refresh `--dry-run` valida configuracion y no consulta servicios remotos; sin `--dry-run`, Sprint 1 sigue bloqueado con mensaje stub.
- **edge_cases:** Quedan definidos los casos invalidos: entorno desconocido, paises vacios o fuera de ISO3 IGAD permitido, anos no enteros, rango invertido, `max_remote_pixels <= 0`, rutas vacias, log level invalido y `MWANGAZA_GEE_PRIVATE_KEY_JSON` presente pero no JSON object valido. Placeholders como `replace-me` no bloquean en `test` o `demo`, pero cuentan como ausentes en `production`.
- **ui_states:** Dashboard muestra perfil activo, paises habilitados, periodo de climatologia y estado `configuration ok` o `configuration invalid`. Los errores son accionables y saneados, con nombres de variables o campos invalidos, sin secretos ni valores privados. En `production` invalido no continua mostrando datos ni claims operativos.

<!-- harness:sprint-2-gee-authentication -->
## sprint-2-gee-authentication · Sprint 2 - Google Earth Engine Authentication



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/api/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/ui/**`
  - `tests/**`
  - `.env.example`
  - `README.md`
  - `pyproject.toml`
  - `docs/**`
  - `spec/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Contrato publico definido bajo `gee` en `/health` y en `GeeAuthResult.to_public_dict()`: `status` literal `ok|auth_error|permission_error|quota_error|network_error`; `configured` bool; `project_configured` bool; `service_account_configured` bool; `checked_at` ISO8601 UTC string; `attempts` int; `max_attempts` int; `message` string saneado; `missing_required_variables` list[str]; `error_code` string estable opcional. Nunca incluye project id, service account, private key ni payload JSON.
- **external_contracts:** Contrato canonico: modulo `src/mwangaza/gee/auth.py`; dataclass `GeeAuthResult`; funcion `check_gee_auth(settings: Settings | None = None, *, ee_module: object | None = None, max_attempts: int | None = None, base_delay_seconds: float = 0.1, sleep: Callable[[float], None] | None = None) -> GeeAuthResult`. `max_attempts` default 3. Backoff exponencial `base_delay_seconds * 2 ** (attempt - 1)`. `settings.max_remote_pixels` solo se usa como configuracion existente, no para consultar datos. API `/health` incluye `gee` usando el mismo resultado saneado. No se anade endpoint nuevo en Sprint 2.
- **edge_cases:** Casos cerrados: SDK `ee` no instalado devuelve `auth_error`; local/test/demo sin credenciales no autentican remotamente y devuelven `auth_error` con `configured=false` solo si se llama al health GEE; JSON malformado, JSON no objeto, campos minimos ausentes o `private_key` ausente devuelven `auth_error`; timeout devuelve `network_error`; cuota devuelve `quota_error`; permisos o proyecto incorrecto devuelven `permission_error`; credenciales revocadas devuelven `auth_error`.
- **ui_states:** El dashboard muestra un estado GEE saneado y compacto: `gee.status`, `configured`, `attempts` y mensaje generico, sin valores de credenciales. En local/test/demo puede mostrar `auth_error/configured=false` sin bloquear el resto del placeholder. En production con configuracion invalida no muestra claims operativos.

<!-- harness:sprint-3-igad-region-catalog -->
## sprint-3-igad-region-catalog · Sprint 3 - IGAD Region Catalog



### Scope aprobado

  - `src/mwangaza/regions/**`
  - `data/regions/**`
  - `tests/regions/**`
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

<!-- harness:sprint-4-data-contracts -->
## sprint-4-data-contracts · Sprint 4 - Data Contracts



### Scope aprobado

  - `src/mwangaza/contracts/**`
  - `tests/contracts/**`
  - `tests/fixtures/contracts/**`
  - `docs/contracts.md`
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

<!-- harness:sprint-5-current-ndvi -->
## sprint-5-current-ndvi · Sprint 5 - Current NDVI



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-6-ndvi-climatology -->
## sprint-6-ndvi-climatology · Sprint 6 - NDVI Climatology



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-7-ndvi-anomaly -->
## sprint-7-ndvi-anomaly · Sprint 7 - NDVI Anomaly



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

### Contexto técnico

- **data_model:** Retorna `Anomaly` NDVI con trazabilidad y valores derivados.
- **external_contracts:** `mwangaza.data.anomaly` con config explicita.
- **edge_cases:** Denominadores cercanos a cero, signo negativo y stddev insuficiente.
- **ui_states:** Sin UI nueva; distingue no disponible de cero.

<!-- harness:sprint-8-current-rainfall -->
## sprint-8-current-rainfall · Sprint 8 - Current Rainfall



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

### Contexto técnico

- **data_model:** Retorna `IndicatorObservation` de lluvia acumulada en mm con cobertura temporal.
- **external_contracts:** `mwangaza.data.rainfall` con adapter mockeable.
- **edge_cases:** UTC, dias inclusivos y validacion de periodo efectivo.
- **ui_states:** Sin UI nueva; estados listos para mostrar cobertura.

<!-- harness:sprint-9-rainfall-climatology -->
## sprint-9-rainfall-climatology · Sprint 9 - Rainfall Climatology



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-10-rainfall-anomaly -->
## sprint-10-rainfall-anomaly · Sprint 10 - Rainfall Anomaly



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-11-current-land-surface-temperature -->
## sprint-11-current-land-surface-temperature · Sprint 11 - Current Land Surface Temperature



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-12-temperature-anomaly -->
## sprint-12-temperature-anomaly · Sprint 12 - Temperature Anomaly



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-13-spatial-aggregation -->
## sprint-13-spatial-aggregation · Sprint 13 - Spatial Aggregation



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-14-indicator-snapshot -->
## sprint-14-indicator-snapshot · Sprint 14 - Indicator Snapshot



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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
  - `src/mwangaza/db/**`

<!-- harness:sprint-15-parquet-cache -->
## sprint-15-parquet-cache · Sprint 15 - Parquet Cache



### Scope aprobado

  - `src/mwangaza/cache/**`
  - `data/cache/.gitkeep`
  - `tests/cache/**`
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

<!-- harness:sprint-16-refresh-pipeline -->
## sprint-16-refresh-pipeline · Sprint 16 - Refresh Pipeline



### Scope aprobado

  - `src/mwangaza/pipeline/**`
  - `src/mwangaza/cli.py`
  - `tests/pipeline/**`
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

<!-- harness:sprint-17-data-quality -->
## sprint-17-data-quality · Sprint 17 - Data Quality



### Scope aprobado

  - `src/mwangaza/quality/**`
  - `tests/quality/**`
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

<!-- harness:sprint-18-alert-thresholds -->
## sprint-18-alert-thresholds · Sprint 18 - Alert Thresholds



### Scope aprobado

  - `src/mwangaza/alerts/thresholds.py`
  - `config/thresholds/**`
  - `tests/alerts/test_thresholds.py`
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

<!-- harness:sprint-19-composite-drought-score -->
## sprint-19-composite-drought-score · Sprint 19 - Composite Drought Score



### Scope aprobado

  - `src/mwangaza/risk/**`
  - `config/risk_models/**`
  - `tests/risk/**`
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

<!-- harness:sprint-20-early-action-recommendations -->
## sprint-20-early-action-recommendations · Sprint 20 - Early Action Recommendations



### Scope aprobado

  - `src/mwangaza/actions/**`
  - `config/actions/**`
  - `tests/actions/**`
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

<!-- harness:sprint-21-alert-persistence -->
## sprint-21-alert-persistence · Sprint 21 - Alert Persistence



### Scope aprobado

  - `src/mwangaza/db/**`
  - `src/mwangaza/alerts/repository.py`
  - `tests/db/**`
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

<!-- harness:sprint-22-dashboard-shell -->
## sprint-22-dashboard-shell · Sprint 22 - Dashboard Shell



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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

<!-- harness:sprint-23-regional-risk-map -->
## sprint-23-regional-risk-map · Sprint 23 - Regional Risk Map



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
  - `tests/maps/**`
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
  - `src/mwangaza/maps/**`
  - `smoke_tests/**`

### Contexto tecnico

- **external_contracts:** El dashboard intenta primero `mwangaza.services.live_gee_dashboard.load_live_gee_dashboard_payloads(...)` para consultar GEE en modo `live` con region y periodo acotados. Si GEE no esta configurado o falla, baja a cache local y luego demo.
- **auth_secrets:** Las credenciales GEE siguen entrando solo por variables de entorno existentes; no se renderizan en HTML, payloads ni cache.
- **ui_states:** El origen visible distingue `live`, `cache` y `demo`; un fallo live no rompe la UI.

<!-- harness:sprint-24-country-drilldown -->
## sprint-24-country-drilldown · Sprint 24 - Country Drilldown



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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

<!-- harness:sprint-25-subnational-pilot -->
## sprint-25-subnational-pilot · Sprint 25 - Subnational Pilot



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`

<!-- harness:sprint-26-temporal-slider -->
## sprint-26-temporal-slider · Sprint 26 - Temporal Slider



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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

<!-- harness:sprint-27-indicator-trends -->
## sprint-27-indicator-trends · Sprint 27 - Indicator Trends



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `assets/**`
  - `tests/ui/**`
  - `tests/services/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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

<!-- harness:sprint-28-active-alerts -->
## sprint-28-active-alerts · Sprint 28 - Active Alerts



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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
  - `src/mwangaza/api/**`
  - `src/mwangaza/contracts/**`
  - `src/mwangaza/db/**`
  - `tests/api/**`

<!-- harness:sprint-29-historical-comparison -->
## sprint-29-historical-comparison · Sprint 29 - Historical Comparison



### Scope aprobado

  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`
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
  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`

<!-- harness:sprint-30-exposure-estimation -->
## sprint-30-exposure-estimation · Sprint 30 - Exposure Estimation



### Scope aprobado

  - `src/mwangaza/data/**`
  - `src/mwangaza/gee/**`
  - `src/mwangaza/contracts/**`
  - `tests/data/**`
  - `tests/fixtures/**`
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
  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`

<!-- harness:sprint-31-executive-pdf-report -->
## sprint-31-executive-pdf-report · Sprint 31 - Executive PDF Report



### Scope aprobado

  - `src/mwangaza/reports/**`
  - `templates/reports/**`
  - `assets/reporting/**`
  - `tests/reports/**`
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
  - `app.py`
  - `src/mwangaza/ui/**`
  - `src/mwangaza/services/**`
  - `assets/**`
  - `tests/ui/**`


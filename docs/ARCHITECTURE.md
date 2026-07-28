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

<!-- harness:sprint-32-data-export -->
## sprint-32-data-export · Sprint 32 - Data Export



### Scope aprobado

  - `src/mwangaza/exports/**`
  - `tests/exports/**`
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

<!-- harness:sprint-33-public-api -->
## sprint-33-public-api · Sprint 33 - Public API



### Scope aprobado

  - `src/mwangaza/api/**`
  - `src/mwangaza/contracts/**`
  - `src/mwangaza/db/**`
  - `tests/api/**`
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

<!-- harness:sprint-34-audit-trail -->
## sprint-34-audit-trail · Sprint 34 - Audit Trail



### Scope aprobado

  - `src/mwangaza/audit/**`
  - `src/mwangaza/db/migrations/**`
  - `tests/audit/**`
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

<!-- harness:sprint-35-notification-simulator -->
## sprint-35-notification-simulator · Sprint 35 - Notification Simulator



### Scope aprobado

  - `src/mwangaza/notifications/**`
  - `templates/notifications/**`
  - `tests/notifications/**`
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

<!-- harness:sprint-36-forecast-model -->
## sprint-36-forecast-model · Sprint 36 - Forecast Model



### Scope aprobado

  - `src/mwangaza/forecasting/**`
  - `tests/forecasting/**`
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

<!-- harness:sprint-37-forecast-confidence -->
## sprint-37-forecast-confidence · Sprint 37 - Forecast Confidence



### Scope aprobado

  - `src/mwangaza/forecasting/confidence.py`
  - `tests/forecasting/test_confidence.py`
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

<!-- harness:sprint-38-multilingual-interface -->
## sprint-38-multilingual-interface · Sprint 38 - Multilingual Interface



### Scope aprobado

  - `locales/**`
  - `src/mwangaza/i18n/**`
  - `tests/i18n/**`
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

<!-- harness:sprint-39-low-bandwidth-mode -->
## sprint-39-low-bandwidth-mode · Sprint 39 - Low-Bandwidth Mode



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

<!-- harness:sprint-40-pwa-installability -->
## sprint-40-pwa-installability · Sprint 40 - React PWA Migration



### Scope aprobado

  - `frontend/**`
  - `package.json`
  - `package-lock.json`
  - `pnpm-lock.yaml`
  - `vite.config.*`
  - `tsconfig*.json`
  - `eslint.config.*`
  - `tests/frontend/**`
  - `pwa/**`
  - `assets/icons/**`
  - `src/mwangaza/ui/pwa/**`
  - `tests/pwa/**`
  - `app.py`
  - `src/mwangaza/api/**`
  - `src/mwangaza/ui/**`
  - `tests/api/**`
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

### Contexto técnico

- **data_model:** Contratos API y fixtures demo definidos para React.
- **external_contracts:** React/Vite como frontend canonico; FastAPI permanece backend.
- **edge_cases:** Responsive, low-bandwidth, i18n y payload parcial cubiertos.
- **ui_states:** Paridad visible con Streamlit definida.

<!-- harness:sprint-41-admin-configuration -->
## sprint-41-admin-configuration · Sprint 41 - Admin Configuration



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/admin/**`
  - `src/mwangaza/api/**`
  - `src/mwangaza/audit/**`
  - `src/mwangaza/db/**`
  - `src/mwangaza/alerts/**`
  - `src/mwangaza/actions/**`
  - `config/thresholds/**`
  - `config/actions/**`
  - `tests/admin/**`
  - `tests/api/**`
  - `tests/audit/**`
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

- **data_model:** Versiones append-only para umbrales y acciones.
- **external_contracts:** `/api/v1/admin/**` y frontend React canónico.
- **edge_cases:** Concurrencia, invalidación y no recalculo cubiertos.
- **ui_states:** Acceso público, editor, validación, historial y modo lite.

<!-- harness:sprint-42-observability -->
## sprint-42-observability · Sprint 42 - Observability



### Scope aprobado

  - `src/mwangaza/observability/**`
  - `tests/observability/**`
  - `src/mwangaza/api/**`
  - `src/mwangaza/contracts/**`
  - `src/mwangaza/db/**`
  - `tests/api/**`
  - `frontend/**`
  - `tests/frontend/**`
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

<!-- harness:sprint-43-security-and-privacy -->
## sprint-43-security-and-privacy · Sprint 43 - Security and Privacy



### Scope aprobado

  - `docs/security/**`
  - `src/mwangaza/security/**`
  - `tests/security/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `frontend/public/**`
  - `.github/workflows/security.yml`
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

<!-- harness:sprint-44-automated-testing -->
## sprint-44-automated-testing · Sprint 44 - Automated Testing



### Scope aprobado

  - `tests/**`
  - `.github/workflows/ci.yml`
  - `.harness/**`
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

<!-- harness:sprint-45-somalia-end-to-end-scenario -->
## sprint-45-somalia-end-to-end-scenario · Sprint 45 - Somalia End-to-End Scenario



### Scope aprobado

  - `tests/e2e/test_somalia_scenario.py`
  - `tests/fixtures/scenarios/somalia/**`
  - `scripts/demo_somalia.py`
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

<!-- harness:sprint-46-northern-kenya-end-to-end-scenario -->
## sprint-46-northern-kenya-end-to-end-scenario · Sprint 46 - Northern Kenya End-to-End Scenario



### Scope aprobado

  - `scripts/demo_kenya.py`
  - `.demo/**`
  - `docs/region-interface.md`
  - `docs/reports-interface.md`
  - `docs/notification-simulator.md`
  - `docs/i18n.md`
  - `docs/README.md`
  - `spec/sprint-46-northern-kenya-end-to-end-scenario-*/**`
  - `src/**/demo/**`
  - `src/**/region*/**`
  - `src/**/reports*/**`
  - `src/**/notifications/**`
  - `frontend/src/routes/region/**`
  - `frontend/src/routes/reports/**`
  - `frontend/src/components/**`
  - `tests/demo/**`
  - `tests/ui/**`
  - `tests/notifications/**`
  - `tests/reports/**`

### Contexto técnico

- **data_model:** El escenario usa exactamente tres unidades subnacionales estables: Turkana (`KEN-023`), Marsabit (`KEN-010`) e Isiolo (`KEN-011`), todas enlazadas al `snapshot_id` común `northern-kenya-2026-03-demo-v1`. Turkana es la unidad destacada por mayor severidad. Cada unidad expone `unit_id`, nombre, severidad, score e indicadores, y mapa, detalle, reporte, alerta y notificación deben referenciar conjuntamente `snapshot_id` y `unit_id`. El estado demo idempotente se persiste por esos identificadores.
- **external_contracts:** La entrada principal verificable es `python scripts/demo_kenya.py`, con fixture local versionado y estado por defecto en `.demo/kenya-state.json`. El JSON de salida debe incluir como mínimo `status`, `mode`, `offline`, `snapshot_id`, `units`, `selected_unit`, `highlighted_unit`, `detail`, `report`, `alert`, `notification`, `requested_language`, `effective_language` y `warnings`. No debe realizar llamadas de red ni depender de credenciales.
- **edge_cases:** La unidad de mayor severidad se resuelve determinísticamente por severidad, luego por score descendente y finalmente por `unit_id` ascendente. Una unidad con datos parciales sigue siendo seleccionable y muestra `unknown` en campos ausentes. Una unidad sin geometría debe seguir funcionando vía tabla accesible. La ausencia de reporte obligatorio bloquea la finalización del escenario.
- **ui_states:** La vista debe mostrar de forma visible el nombre y `unit_id` activos, badge de severidad, score e indicadores justificativos. El mapa o la tabla accesible permiten cambiar la selección sin recarga remota. El reporte debe reflejar el mismo `unit_id` de la unidad activa. La vista previa de notificación debe exponer idioma solicitado y efectivo, incluyendo fallback.

<!-- harness:sprint-47-offline-demo-fallback -->
## sprint-47-offline-demo-fallback · Sprint 47 - Offline Demo Fallback



### Scope aprobado

  - `demo_data/**`
  - `.demo/**`
  - `scripts/reset_demo.py`
  - `scripts/demo_somalia.py`
  - `scripts/demo_kenya.py`
  - `src/**/config/**`
  - `src/**/demo/**`
  - `src/**/api/**`
  - `src/**/services/**`
  - `src/**/alerts/**`
  - `src/**/reports/**`
  - `src/**/ui/**`
  - `frontend/src/**`
  - `frontend/public/**`
  - `tests/demo/**`
  - `tests/**/api/**`
  - `tests/**/ui/**`
  - `tests/**/reports/**`
  - `docs/configuration.md`
  - `docs/contracts.md`
  - `docs/dashboard-shell.md`
  - `docs/reports-interface.md`
  - `docs/DECISIONS.md`

### Contexto técnico

- **data_model:** `is_demo=true` queda como marca canónica aditiva para todos los datos derivados de fixtures demo: overview, region, alerts, reports, forecast diagnostics, exports, configuración y outbox. `is_simulated=true` se conserva solo donde ya exista: `is_demo` describe el origen del dato y `is_simulated` que no hubo entrega o acción real. Todo dato demo debe exponer además `reference_date` o `snapshot_id`.
- **external_contracts:** La activación contractual única del modo es `MWANGAZA_MODE=demo`. `scripts/reset_demo.py` es el reset oficial. Los payloads API en demo añaden `is_demo`, `reference_date` o `snapshot_id`, y `data_mode=demo`. Deben funcionar offline Overview, Regions, Alerts, Reports, About, Admin y Technical, además de `scripts/demo_somalia.py`, `scripts/demo_kenya.py` y previews/exports locales.
- **edge_cases:** El modo demo valida su baseline al arrancar. Si detecta estado corrupto, parcial o mezclado con registros no demo, bloquea el recorrido con mensaje accionable hasta ejecutar `scripts/reset_demo.py`; no hay sobrescritura automática. El reset elimina únicamente el estado demo gestionado y restaura el baseline de forma idempotente. Esto también cubre reinstalaciones/refrescos offline: el baseline debe validarse antes de servir datos demo.
- **ui_states:** El banner demo debe mostrar siempre como mínimo “Demo data”, origen offline, `reference_date`, `snapshot_id` y referencia al comando oficial de reset. Debe permanecer visible en Overview, Regions, Alerts, Reports, About, Admin y Technical, incluidos estados de error y durante la navegación interna.

<!-- harness:sprint-48-data-provenance-documentation -->
## sprint-48-data-provenance-documentation · Sprint 48 - Data Provenance Documentation



### Scope aprobado

  - `docs/about-interface.md`
  - `docs/contracts.md`
  - `docs/thresholds.md`
  - `docs/ARCHITECTURE.md`
  - `docs/data-provenance.md`
  - `frontend/src/App.tsx`
  - `frontend/src/styles.css`
  - `tests/frontend/app.test.tsx`
  - `tests/frontend/smoke.test.tsx`

### Contexto técnico

- **data_model:** La feature debe definir un inventario canónico versionado y legible por máquina en `docs/data-sources/catalog.json`, reutilizado como fuente de verdad de `docs/data-provenance.md` y de la vista `/about/provenance`. Cada entrada del catálogo incluye como mínimo `source_name`, `variable_or_indicator`, `unit`, `spatial_or_temporal_resolution`, `update_frequency`, `license_or_terms`, `applicable_modes`, `latency` y `limitations`.
- **external_contracts:** El contrato navegable queda fijado en la ruta interna estable `/about/provenance`, enlazada desde `/about` y reutilizable como referencia durable desde reportes. La documentación persistente equivalente vive en `docs/data-provenance.md`, y el catálogo fuente de verdad en `docs/data-sources/catalog.json`.
- **edge_cases:** La documentación debe separar de forma explícita las variantes `live`, `cache` y `demo` cuando cambien procedencia, latencia o cobertura. `demo` y cualquier dato simulated deben quedar claramente diferenciados de los datos operativos. `cache` conserva la procedencia original y añade la antigüedad. Si una misma variable usa distintas fuentes o coberturas según modo o país, el catálogo debe reflejar esa variante sin ambigüedad. `exposure` solo muestra fuente/año/resolución cuando existan datos disponibles para esta release.
- **ui_states:** `/about` debe mostrar un CTA visible con el texto `Data provenance and methodology` dentro de la sección Methodology. Ese enlace navega a la vista dedicada `/about/provenance`, que debe renderizar de forma visible el catálogo, las definiciones, las limitaciones, los umbrales etiquetados como no oficiales/configurables y un diagrama de linaje. Si existe contenido pendiente de verificación, la advertencia debe ser visible en esa misma vista.

<!-- harness:sprint-49-public-readme -->
## sprint-49-public-readme · Sprint 49 - Public README



### Scope aprobado

  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/README.md`
  - `docs/configuration.md`
  - `docs/security/**`
  - `.github/workflows/ci.yml`
  - `Makefile`
  - `tests/**`
  - `spec/**`
  - `progress/**`

### Contexto técnico

- **data_model:** La feature sigue siendo documental y no introduce contratos de datos nuevos. El README debe apoyarse en los modelos y catálogos ya documentados en `docs/`, incluyendo la separación entre modos `live`, `cache` y `demo`, sin redefinir payloads ni estructuras.
- **external_contracts:** La spec ya puede fijar los entrypoints y comandos públicos canónicos que el README puede prometer: `uv sync`, `npm install`, `MWANGAZA_MODE=demo` + `uv run uvicorn mwangaza.api.app:app`, `npm run dev`, `scripts/demo_somalia.py`, `scripts/demo_kenya.py`, `scripts/reset_demo.py`, `uv run python -m unittest discover -s tests`, `npm test`, `npm run typecheck`, `npm run lint` y `npm run build`. El README no debe publicar comandos obsoletos ni nombres que contradigan `docs/ARCHITECTURE.md`.
- **edge_cases:** La spec debe fijar una ruta canónica basada en `uv` y `npm`, documentando equivalentes claros para PowerShell y shells POSIX cuando difiera la sintaxis de variables de entorno. `make` puede aparecer como atajo opcional, pero no como requisito universal. También debe quedar explícito que el README público solo promete recorridos demo soportados actualmente, incluyendo los escenarios versionados de Somalia y Northern Kenya.
- **ui_states:** La feature no cambia la UI. El README solo debe describir estados ya existentes: demo/offline, conectado, limitaciones y roadmap, sin introducir nuevos estados visuales ni pantallas no implementadas.

<!-- harness:sprint-50-landing-page -->
## sprint-50-landing-page · Sprint 50 - Landing Page



### Scope aprobado

  - `frontend/src/**`
  - `frontend/public/**`
  - `frontend/index.html`
  - `frontend/src/router/**`
  - `frontend/src/config/**`
  - `frontend/src/components/**`
  - `frontend/src/pages/**`
  - `tests/frontend/**`
  - `docs/about-interface.md`
  - `README.md`
  - `spec/sprint-50-landing-page-*/**`

### Contexto técnico

- **data_model:** La configuración pública de la landing se define en `frontend/src/config/landing.ts` con los campos `dashboard`, `github` y `demo`. Cada valor debe ser una URL absoluta HTTPS o una ruta interna que empiece por `/`. El componente de la landing admite configuración inyectable en tests para verificar resolución de CTAs por entorno sin depender de secretos.
- **external_contracts:** La landing vive en la ruta pública `/landing` y es estrictamente aditiva. El CTA principal abre `/overview`. La navegación secundaria enlaza `About`, `GitHub` y `demo` desde la configuración pública. `/` y las rutas operativas existentes conservan su comportamiento actual.
- **edge_cases:** La validación responsive cubre 320 px de ancho mínimo y breakpoints de 375/768/1280. Ningún contenedor puede introducir overflow horizontal; textos largos deben hacer wrapping. Las listas de pilotos y limitaciones crecen verticalmente y cualquier grid colapsa a una sola columna en móvil estrecho.
- **ui_states:** La landing no tiene estado de carga ni dependencias remotas. El contenido principal es estático/versionado y no depende de la disponibilidad de los CTAs opcionales. Los CTAs no disponibles se omiten sin mensaje de error y sin dejar huecos visuales.

<!-- harness:sprint-56-region-explorer-completion -->
## sprint-56-region-explorer-completion · Sprint 56 - Region Explorer Completion



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `src/mwangaza/services/live_gee_dashboard.py`
  - `src/mwangaza/services/dashboard_shell.py`
  - `tests/services/**`
  - `smoke_tests/**`
  - `docs/region-interface.md`
  - `docs/contracts.md`
  - `spec/sprint-56-region-explorer-completion-*/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Contrato subnacional completo y equivalente para demo y live GEE, con valores ausentes explícitos.
- **external_contracts:** Deep-link, geometrías y salida completa del pipeline live GEE definidos.
- **edge_cases:** Orden, comparación y selección deterministas.
- **ui_states:** Panel funcional completo en live y demo, low-bandwidth y payload incompleto.

### ADM1 analytical overlay

- Versioned geoBoundaries assets are loaded into the region catalog as `adm1` analytical regions with stable `boundary_iso` and `boundary_id` metadata.
- The live loader computes the current-period indicator snapshot and composite risk per configured ADM1 unit, while country trends and historical comparisons remain aggregated.
- `RegionProfile.administrative_units` is the boundary between processing and presentation. The public API serializes it additively and the React atlas joins it to local geometry by exact `boundary_iso`.
- ADM1 query failures are isolated per unit. Missing units are not synthesized and remain visually unassessed.

<!-- harness:sprint-57-overview-completion -->
## sprint-57-overview-completion · Sprint 57 - Overview Completion



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `src/mwangaza/services/dashboard_shell.py`
  - `src/mwangaza/services/live_gee_dashboard.py`
  - `tests/services/test_live_gee_dashboard.py`
  - `src/mwangaza/reports/**`
  - `src/mwangaza/exports/**`
  - `tests/reports/**`
  - `tests/exports/**`
  - `docs/overview-interface.md`
  - `docs/contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-57-overview-completion-*/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Snapshot procesado con IDs y descargas contextuales aditivas.
- **external_contracts:** Rutas de detalle y endpoints de descarga concretos.
- **edge_cases:** Zoom, selección, orden y comparación deterministas.
- **ui_states:** Cockpit completo, accesible y equivalente en low-bandwidth.

<!-- harness:sprint-58-alerts-center-completion -->
## sprint-58-alerts-center-completion · Sprint 58 - Alerts Center Completion



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `src/mwangaza/contracts/**`
  - `tests/contracts/**`
  - `src/mwangaza/alerts/**`
  - `tests/alerts/**`
  - `src/mwangaza/actions/**`
  - `tests/actions/**`
  - `src/mwangaza/notifications/**`
  - `tests/notifications/**`
  - `src/mwangaza/audit/**`
  - `tests/audit/**`
  - `src/mwangaza/services/dashboard_shell.py`
  - `tests/ui/test_dashboard_shell.py`
  - `src/mwangaza/exports/**`
  - `tests/exports/**`
  - `src/mwangaza/reports/**`
  - `tests/reports/**`
  - `docs/alerts-interface.md`
  - `docs/contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-58-alerts-center-completion-*/**`
  - `progress/**`

### Contexto técnico

- **data_model:** identidad backend y lifecycle append-only.
- **external_contracts:** listado, detalle y export filtrados.
- **edge_cases:** orden, filtros, selección y paginación deterministas.
- **ui_states:** workspace table-first con inspector operativo.

<!-- harness:sprint-59-reports-center-completion -->
## sprint-59-reports-center-completion · Sprint 59 - Reports Center Completion



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `src/mwangaza/reports/**`
  - `tests/reports/**`
  - `src/mwangaza/audit/**`
  - `tests/audit/**`
  - `src/mwangaza/services/dashboard_shell.py`
  - `tests/ui/test_dashboard_shell.py`
  - `docs/reports-interface.md`
  - `docs/executive-report.md`
  - `docs/audit-trail.md`
  - `docs/contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-59-reports-center-completion-*/**`
  - `progress/**`

### Contexto técnico

- **data_model:** La spec debe definir que la API es propietaria de identidad y tiempos. Cada reporte expone `id`, `generated_at`, `updated_at`, `expires_at` opcional, `status` (`queued`, `generating`, `ready`, `failed`, `expired`), `region_id`, `period_start`, `period_end`, `template_id`, `language`, `author`, `snapshot_id`, formatos disponibles y error saneado opcional. IDs y timestamps son estables, UTC ISO-8601, y el navegador no los inventa. Exportaciones recientes y eventos de auditoría tienen IDs propios y referencian al reporte.
- **external_contracts:** La spec aprueba endpoints aditivos bajo `/api/v1/reports` para listar reportes, obtener detalle, generar reportes y descargar PDF/CSV/JSON. La generación usa snapshots materializados y nunca consulta GEE desde el navegador. La auditoría local de generación y descarga sólo se registra si ya existe adapter aprobado. Compartir, programación, mutación de plantillas y distribución permanecen como `pending_contract` sin endpoints públicos.
- **edge_cases:** La spec debe cubrir lista vacía preservando contexto y acción de generación, filtros sin resultados con acción para limpiar filtros, reportes en curso con progreso indeterminado y descarga bloqueada, IDs/timestamps ausentes con degradación explícita sin fallback inventado, duplicados deduplicados por ID backend, expirados conservados en historial pero no descargables, y orden/selección deterministas.
- **ui_states:** La tesis visual queda definida como workspace editorial-operativo table-first, con cabecera y filtros compactos, banda de estado, cola dominante, preview central paginado e inspector lateral sticky. Deben ser visibles los estados loading, empty, filtered-empty, generating, ready, failed, expired, disabled y `pending_contract`. El preview es HTML fiel hasta que exista PDF generado y sólo entonces se etiqueta como PDF. Low-bandwidth conserva filtros, cola, detalle, metadatos y descargas sin decoración pesada.

<!-- harness:sprint-60-about-methodology-completion -->
## sprint-60-about-methodology-completion · Sprint 60 - About and Methodology Completion



### Scope aprobado

  - `frontend/**`
  - `tests/frontend/**`
  - `src/mwangaza/api/**`
  - `tests/api/**`
  - `docs/**`
  - `spec/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Metadata pública y catálogo de fuentes tienen campos, propiedad y degradación definidos.
- **external_contracts:** Endpoint ligero, rutas PWA y navegación están definidos.
- **edge_cases:** Tema, almacenamiento, URLs, metadata inválida y low-bandwidth están cubiertos.
- **ui_states:** Jerarquía editorial, tema, documentos y degradación están definidos.

<!-- harness:sprint-61-probabilistic-training-dataset -->
## sprint-61-probabilistic-training-dataset · Sprint 61 - Probabilistic Training Dataset



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `config/probabilistic/**`
  - `pyproject.toml`
  - `requirements*.txt`
  - `Makefile`
  - `docs/probabilistic-risk.md`
  - `docs/contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-61-probabilistic-training-dataset-*/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Contratos inmutables de entrada, fila, manifest y dataset.
- **external_contracts:** API Python y escritura atómica definidas.
- **edge_cases:** Frecuencia, gaps, ventanas, timestamps y targets exactos.
- **ui_states:** Sin UI; semántica documental explícita.

<!-- harness:sprint-62-calibrated-risk-classifier -->
## sprint-62-calibrated-risk-classifier · Sprint 62 - Calibrated Risk Classifier



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `config/probabilistic/**`
  - `data/models/.gitkeep`
  - `pyproject.toml`
  - `requirements*.txt`
  - `Makefile`
  - `docs/probabilistic-risk.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62-calibrated-risk-classifier-*/**`
  - `progress/**`

<!-- harness:sprint-62b-real-historical-backfill -->
## sprint-62b-real-historical-backfill · Sprint 62B - Real Historical Backfill



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `src/mwangaza/gee/**`
  - `scripts/backfill_probabilistic_history.py`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `data/historical/.gitkeep`
  - `.gitignore`
  - `docs/probabilistic-risk.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62b-real-historical-backfill-*/**`
  - `progress/**`

<!-- harness:sprint-62c-adm1-antecedent-signals -->
## sprint-62c-adm1-antecedent-signals · Sprint 62C - ADM1 Antecedent Drought Signals

`mwangaza.gee.adm1_antecedent` builds one multi-band image per dekad and applies
`reduceRegions` to bounded ADM1 batches. The client materializer batches both
regions and windows, checkpoints canonical JSONL atomically, and stores the 121
version-pinned geometries once in the manifest. Rows reference those geometries
through stable boundary IDs.

`mwangaza.probabilistic.antecedents` is a separate local transformation stage.
It forms complete CHIRPS calendar months, fits empirical SPI distributions only
through a configured reference cutoff, and derives rainfall deficits plus NDVI
persistence and slopes. Provider observations retain `observed_at` and
`available_at`; ECMWF values instead retain creation time as `available_at`,
forecast lead, and a null `observed_at`.

### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `src/mwangaza/gee/**`
  - `scripts/backfill_adm1_antecedent_signals.py`
  - `scripts/prepare_adm1_probabilistic_dataset.py`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `data/historical/.gitkeep`
  - `.gitignore`
  - `docs/data-sources/**`
  - `docs/probabilistic-risk.md`
  - `docs/data-provenance.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62c-adm1-antecedent-signals-*/**`
  - `progress/**`

<!-- harness:sprint-62d-independent-drought-labels -->
## sprint-62d-independent-drought-labels · Sprint 62D - Independent Drought and Food Security Labels



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `scripts/import_independent_labels.py`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `data/historical/.gitkeep`
  - `.gitignore`
  - `docs/data-sources/**`
  - `docs/probabilistic-risk.md`
  - `docs/data-provenance.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62d-independent-drought-labels-*/**`
  - `progress/**`

<!-- harness:sprint-62d2-real-drought-hazard-catalog -->
## sprint-62d2-real-drought-hazard-catalog · Sprint 62D.2 - Real Drought Hazard Catalog



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `scripts/backfill_ndma_drought_phases.py`
  - `scripts/import_independent_labels.py`
  - `scripts/audit_drought_hazard_episodes.py`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `docs/data-sources/**`
  - `docs/probabilistic-risk.md`
  - `docs/data-provenance.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62d2-real-drought-hazard-catalog-*/**`
  - `progress/**`
## Catálogo de drought hazard independiente

El flujo aditivo de 62D.2 tiene tres etapas separadas: backfill NDMA a un manifiesto
oficial validado; normalización NDMA/EM-DAT al contrato de etiquetas independientes; y
auditoría de episodios ADM1. Los artefactos fuente y los episodios no comparten schema ni
se consumen todavía por el entrenamiento. El catálogo de autoridades IGAD hace explícita
la cobertura desconocida antes de añadir adapters futuros.

<!-- harness:sprint-62e-drought-episode-evaluation -->
## sprint-62e-drought-episode-evaluation · Sprint 62E - Drought Episode Evaluation



### Scope aprobado

  - `src/mwangaza/probabilistic/**`
  - `scripts/evaluate_drought_episodes.py`
  - `tests/probabilistic/**`
  - `tests/fixtures/probabilistic/**`
  - `docs/probabilistic-risk.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `spec/sprint-62e-drought-episode-evaluation-*/**`
  - `progress/**`


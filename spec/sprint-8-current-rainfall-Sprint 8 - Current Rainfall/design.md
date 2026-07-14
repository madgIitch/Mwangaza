# sprint-8-current-rainfall · undefined — Diseño

## Scope (archivos que puede tocar)

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

## Enfoque

- **data_model:** Retorna `IndicatorObservation` de lluvia acumulada en mm con cobertura temporal.
- **external_contracts:** `mwangaza.data.rainfall` con adapter mockeable.
- **edge_cases:** UTC, dias inclusivos y validacion de periodo efectivo.
- **ui_states:** Sin UI nueva; estados listos para mostrar cobertura.

## Decisiones de la entrevista

- **data_model:** Sprint 8 produce un `IndicatorObservation` de Sprint 4 con `indicator="rainfall_mm"`, `unit="mm"`, `value` como precipitacion acumulada del periodo y metadata con `expected_days`, `available_days`, `missing_days`, `coverage_fraction`, `actual_period_start`, `actual_period_end`, `collection_id` y `aggregation="sum"`.
- **error_states:** Fechas invertidas, coleccion vacia, conteos negativos, `available_days > expected_days`, acumulados negativos o no finitos fallan con `RainfallProcessingError`. Si no hay pixeles/dias validos, el resultado usa `quality_flag="no_data"` y `value=None`. Si faltan dias por encima del umbral permitido, usa `quality_flag="degraded"` y metadata registra `incomplete_period=true`.
- **edge_cases:** Las fechas de entrada se interpretan como instantes UTC ISO8601. El numero de dias esperados se calcula de forma inclusiva por fecha UTC calendario. La funcion no mezcla periodos: el adaptador debe devolver `actual_period_start` y `actual_period_end`, y estos se validan contra el periodo solicitado. Un periodo parcial se conserva en metadata y no se presenta como completo.
- **auth_secrets:** Sprint 8 no introduce secretos. La coleccion CHIRPS se configura con variable publica `MWANGAZA_RAINFALL_COLLECTION`. Tests usan adaptadores fake y no llaman Earth Engine real.
- **external_contracts:** Contrato publico en `mwangaza.data.rainfall`: `RainfallCollectionConfig`, `RainfallQueryResult`, `RainfallAdapter`, `RainfallProcessingError`, `summarize_rainfall_daily_values(...)` y `compute_current_rainfall(region_id, period_start, period_end, *, adapter, config=None) -> IndicatorObservation`. El adapter expone `query_rainfall(geometry, period_start, period_end, config) -> RainfallQueryResult`.
- **ui_states:** No hay UI nueva. El contrato prepara UI futura para distinguir `ok`, `degraded/incomplete_period` y `no_data`, mostrando milimetros acumulados solo cuando hay valor valido.
- **rollback_compat:** No se rompen Sprints 0-7. Se reutilizan `Settings`, catalogo de regiones y contratos existentes. `MWANGAZA_NDVI_COLLECTION` se mantiene intacta; lluvia usa `MWANGAZA_RAINFALL_COLLECTION` con default CHIRPS.
- **tests:** Tests bajo `tests/data/**` cubren acumulado en mm, conteos esperados/disponibles, `incomplete_period`, `no_data`, interpretacion UTC, rechazo de periodos mezclados, configuracion por entorno y ausencia de llamadas remotas.


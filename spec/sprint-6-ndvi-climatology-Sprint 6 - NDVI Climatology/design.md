# sprint-6-ndvi-climatology · undefined — Diseño

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

## Decisiones de la entrevista

- **data_model:** Sprint 6 produce un `Baseline` de Sprint 4 con `indicator="ndvi"`, `unit="index"`, `baseline_start_year`, `baseline_end_year`, `mean`, `median`, `stddev`, `observations`, `quality_flag`, `source` y metadata con `effective_years`, `excluded_years`, `min_years`, `season_start`, `season_end`, `period_key`, `baseline_version` y `collection_id`. La version de baseline se deriva de region, indicador, ventana histórica, season y colección.
- **error_states:** Fechas estacionales inválidas, ventana histórica invertida, año actual incluido en baseline, region inexistente o valores NDVI no finitos fallan con `ClimatologyError`. Si los años efectivos son menos que `min_years`, se devuelve `Baseline` con `quality_flag="insufficient_history"` y estadísticos `None`, no se inventa valor.
- **edge_cases:** La ventana histórica se interpreta como años completos inclusivos. El período actual nunca se incluye aunque caiga dentro de la ventana configurada; se excluye y se registra en `excluded_years`. Se soportan ventanas estacionales que cruzan año calendario, por ejemplo diciembre-enero, calculando fechas por año sin mezclar con el periodo actual. Meses con distinta duración se validan usando fechas ISO reales.
- **auth_secrets:** Sprint 6 no introduce secretos. Los tests usan adaptador fake y no llaman Earth Engine real. La futura integración GEE queda detrás de `query_ndvi_year(...)`, sin leer credenciales en tests ni logs.
- **external_contracts:** Contrato publico en `mwangaza.data.climatology`: `ClimatologyConfig`, `ClimatologyYearObservation`, `ClimatologyError`, `compute_ndvi_climatology(region_id, season_start, season_end, current_period_start, current_period_end, *, adapter, config=None) -> Baseline`. El adapter expone `query_ndvi_year(geometry, year, season_start, season_end, config) -> ClimatologyYearObservation`. Configuracion externa: `MWANGAZA_CLIMATOLOGY_START_YEAR`, `MWANGAZA_CLIMATOLOGY_END_YEAR`, `MWANGAZA_CLIMATOLOGY_MIN_YEARS` y `MWANGAZA_NDVI_COLLECTION`.
- **ui_states:** No hay UI nueva. Los contratos permiten mostrar baseline con `quality_flag=ok` o `insufficient_history`; UI futura debe distinguir baseline insuficiente de valor cero.
- **rollback_compat:** No se rompen Sprints 0-5. Se reutilizan `Baseline`, region catalog, configuración existente de climatología y colección NDVI. No se añaden dependencias pesadas; estadística con stdlib.
- **tests:** Tests bajo `tests/data/**` cubren: usa solo años configurados, excluye periodo actual, calcula mean/median/stddev/observations, insuficientes años -> `insufficient_history`, cambiar ventana/coleccion cambia version, cambio de año y meses con distinta duración, no llamadas remotas.


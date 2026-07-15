# sprint-11-current-land-surface-temperature · undefined — Diseño

## Scope (archivos que puede tocar)

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

- **data_model:** Sprint 11 produce un `IndicatorObservation` con `indicator="lst_c"`, `unit="celsius"` y `value` como media regional en Celsius. Metadata incluye `mean_c`, `median_c`, `valid_pixel_count`, `total_pixel_count`, `coverage_fraction`, `actual_period_start`, `actual_period_end`, `collection_id`, `aggregation`, y detalle saneado de conversion/calidad.
- **error_states:** Fechas invertidas, periodo efectivo distinto, conteos negativos, `valid_pixel_count > total_pixel_count`, escala o offset no finitos, valores no finitos y temperaturas fuera de rango fisico configurable fallan con `LstProcessingError` o devuelven `quality_flag="invalid"` cuando el resultado agregado es fisicamente imposible. Sin pixeles validos devuelve `value=None`, `quality_flag="no_data"`.
- **edge_cases:** Las fechas son ISO8601 con timezone y se normalizan a UTC. Pixeles sin calidad se omiten antes de agregacion. Kelvin se convierte a Celsius con `raw * scale + offset - 273.15` dentro del adaptador/summarizer. La mediana se calcula deterministamente sobre valores validos ordenados.
- **auth_secrets:** Sprint 11 no introduce secretos ni llamadas remotas obligatorias. La coleccion LST se configura con identificador publico y tests usan adaptadores fake.
- **external_contracts:** Contrato publico en `mwangaza.data.lst`: `LstCollectionConfig`, `LstQueryResult`, `LstAdapter`, `LstProcessingError`, `summarize_lst_raw_values(...)` y `compute_current_lst(region_id, period_start, period_end, *, adapter, config=None) -> IndicatorObservation`.
- **ui_states:** No hay UI nueva. El contrato prepara UI futura para mostrar Celsius, cobertura y distinguir `ok`, `degraded`, `no_data` e `invalid`.
- **rollback_compat:** Mantiene Sprints 0-10. No cambia contratos de NDVI, lluvia o anomalias. Usa el indicador `lst_c` ya permitido por contratos.
- **tests:** Tests bajo `tests/data/**` cubren conversion Kelvin/Celsius, mascara de calidad, media, mediana, cobertura, periodo efectivo, valores fisicamente imposibles, no data, configuracion de coleccion y ausencia de llamadas remotas.


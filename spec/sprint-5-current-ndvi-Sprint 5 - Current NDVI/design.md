# sprint-5-current-ndvi · undefined — Diseño

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

- **data_model:** Sprint 5 produce un `IndicatorObservation` de Sprint 4 con `indicator="ndvi"`, `unit="index"`, `source` igual a la coleccion configurada, `quality_flag`, `is_simulated` y metadata con `valid_pixel_fraction`, `valid_pixel_count`, `total_pixel_count`, `collection_id`, `scale_factor` y `actual_period_start/end`. El valor NDVI se expresa ya escalado en rango esperado `[-1.0, 1.0]`.
- **error_states:** Una region sin pixeles validos devuelve `IndicatorObservation(value=None, quality_flag="no_data")`, no cero. Region inexistente falla con error controlado del catalogo/contrato. Fechas invertidas fallan con `NdviProcessingError`. Respuestas del adaptador con conteos invalidos, NDVI fuera de rango tras escalado o geometria/periodo ausente fallan con `NdviProcessingError`.
- **edge_cases:** El periodo real observado puede ser menor que la ventana solicitada y se conserva en metadata `actual_period_start/end`; el contrato conserva `period_start/end` como periodo real usado en la observacion final. Pixeles con QA no valida o valor raw nulo se excluyen del numerador y denominador valido. `valid_pixel_fraction` se calcula como `valid_pixel_count / total_pixel_count` y es `0.0` cuando no hay datos validos.
- **auth_secrets:** Sprint 5 no introduce secretos. Usa el adaptador GEE ya autenticado en Sprint 2 cuando se integre, pero los tests pasan un fake adapter y no llaman red ni leen credenciales. No se loguean claves ni `.env`.
- **external_contracts:** Contrato publico en `mwangaza.data.ndvi`: `NdviCollectionConfig`, `NdviQueryResult`, `NdviProcessingError`, `compute_current_ndvi(region_id, period_start, period_end, *, adapter, config=None) -> IndicatorObservation`. El adaptador debe exponer `query_ndvi(geometry, period_start, period_end, config) -> NdviQueryResult`. La coleccion por defecto es configurable con `MWANGAZA_NDVI_COLLECTION` y por argumento `NdviCollectionConfig`.
- **ui_states:** Sprint 5 no cambia UI. Futuras vistas podran mostrar `quality_flag`, `valid_pixel_fraction` y periodo real. Si `quality_flag=no_data`, UI futura no debe mostrar verde ni valor cero.
- **rollback_compat:** No se rompen Sprints 0-4. `IndicatorObservation` sigue validando region IDs y NDVI. `make lint/typecheck/test`, `/health`, GEE auth, region catalog y contracts siguen importables. La nueva config de coleccion tiene default seguro y no es secreta.
- **tests:** Tests bajo `tests/data/**` usan fake adapter para verificar: valor escalado en rango, QA invalida excluida, sin pixeles validos -> `no_data`, coleccion configurable, geometria y fechas pasadas al adapter, periodo real preservado, fraccion de cobertura en metadata y ausencia de llamadas GEE reales.


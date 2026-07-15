# sprint-9-rainfall-climatology · undefined — Diseño

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

- **data_model:** Sprint 9 produce un baseline historico de precipitacion compatible con Sprint 4 y Sprint 8: `indicator="rainfall_mm"`, `unit="mm"`, estadisticas `mean`, `median`, `percentile_20`, `percentile_50`, `percentile_80`, `stddev`, lista de `included_years`, lista de `excluded_years` con motivo, `sample_size`, `min_years`, `baseline_version` y metadata de fuente, ventana y cobertura. El baseline no inventa valores para anos sin cobertura suficiente.
- **error_states:** Fechas invertidas, `min_years <= 0`, cobertura minima fuera de rango, acumulados negativos o no finitos, resultados sin ano calendario o periodos efectivos incoherentes fallan con `RainfallClimatologyError`. Si tras excluir anos insuficientes no se alcanza `min_years`, se devuelve baseline no disponible con calidad `insufficient_history`, estadisticas `None`, anos excluidos registrados y sin representar climatologia como cero.
- **edge_cases:** La ventana equivalente preserva mes/dia UTC del periodo objetivo para cada ano historico. El 29 de febrero usa una politica explicita configurable y por defecto se omite en anos no bisiestos registrando exclusion. Percentiles se calculan de forma determinista sobre acumulados incluidos ordenados. La desviacion usa poblacion cuando hay al menos dos valores y `None` si no hay muestra suficiente.
- **auth_secrets:** Sprint 9 no introduce secretos ni llamadas remotas obligatorias. Reutiliza la coleccion publica `MWANGAZA_RAINFALL_COLLECTION` de Sprint 8 y tests con adaptadores fake. No se leen ni escriben credenciales.
- **external_contracts:** Contrato publico en `mwangaza.data.rainfall_climatology`: `RainfallClimatologyConfig`, `HistoricalRainfallYear`, `RainfallClimatologyBaseline`, `RainfallClimatologyError`, `compute_rainfall_climatology(region_id, period_start, period_end, *, years, adapter, config=None) -> RainfallClimatologyBaseline`. El adapter reutiliza el contrato de Sprint 8 por ano equivalente.
- **ui_states:** No hay UI nueva. El contrato prepara UI futura para distinguir baseline disponible, `insufficient_history` y anos excluidos. Las estadisticas no disponibles se exponen como `None`, no como cero.
- **rollback_compat:** Mantiene Sprints 0-8. No cambia `compute_current_rainfall(...)`, contratos de NDVI, settings existentes ni variables de secretos. La climatologia de lluvia vive en modulo nuevo y puede convivir con Sprint 8 sin modificar su API publica.
- **tests:** Tests bajo `tests/data/**` cubren media, mediana, percentiles 20/50/80, desviacion, exclusion por cobertura insuficiente, minimo configurable de anos, version del baseline ante cambios de fuente o ventana, distribucion sesgada, valores extremos, fechas UTC y ausencia de llamadas remotas.


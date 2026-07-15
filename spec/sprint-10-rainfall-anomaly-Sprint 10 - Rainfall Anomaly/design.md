# sprint-10-rainfall-anomaly · undefined — Diseño

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

- **data_model:** Sprint 10 produce un `Anomaly` contractual con `indicator="rainfall_mm"`, `unit="mm"`, `method="current_minus_mean"` y `value` como anomalia absoluta en mm. Metadata incluye `absolute_anomaly`, `percent_anomaly`, `empirical_percentile`, `current_value`, `baseline_mean`, `baseline_id`, `current_id`, `classification` tecnica y motivos de no disponibilidad.
- **error_states:** Indicador/unidad incompatibles, regiones distintas, lluvia negativa o no finita, baseline sin distribucion historica suficiente y configuracion invalida fallan con `RainfallAnomalyError` o devuelven `quality_flag` no concluyente cuando la entrada contractual ya indica `no_data` o `insufficient_history`. No se inventa percentil si faltan observaciones historicas.
- **edge_cases:** Anomalia negativa significa deficit frente a la media. El porcentaje se omite si la media esta dentro de epsilon. El percentil empirico usa conteo determinista `<= current` sobre valores historicos incluidos y queda acotado entre 0 y 100. Umbrales internos documentados: `deficit_threshold_percent=-20.0` y `excess_threshold_percent=20.0`.
- **auth_secrets:** Sprint 10 no introduce secretos ni red. Solo consume objetos ya calculados por Sprints 8 y 9 y tests con fixtures/fakes locales.
- **external_contracts:** Contrato publico en `mwangaza.data.rainfall_anomaly`: `RainfallAnomalyConfig`, `RainfallAnomalyError`, `compute_rainfall_anomaly(current, baseline, *, config=None) -> Anomaly`. `baseline` puede ser `RainfallClimatologyBaseline` o `Baseline` con metadata compatible.
- **ui_states:** No hay UI nueva. Metadata distingue `deficit`, `normal`, `excess` y no concluyente para UI futura, sin severidad final ni acciones.
- **rollback_compat:** Mantiene Sprints 0-9. No cambia contratos de NDVI ni APIs de lluvia actual/climatologia. Reutiliza `Anomaly` existente sin anadir payload nuevo.
- **tests:** Tests bajo `tests/data/**` cubren deficit negativo, exceso positivo, percentil 0..100, percentil no disponible por minimo configurable, trazabilidad, propagacion de calidad, umbrales internos exactos y ausencia de alertas/severidad/acciones.


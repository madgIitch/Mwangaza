# sprint-12-temperature-anomaly · undefined — Diseño

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

- **data_model:** Sprint 12 produce una climatologia LST como `Baseline` con `indicator="lst_c"` y `unit="celsius"`, y una anomalia como `Anomaly` con `indicator="lst_c"`, `unit="celsius"` y `value=current.value - baseline.mean`. Metadata conserva `product_variant` (`day` o `night`), anos incluidos/excluidos, `baseline_version`, `absolute_anomaly_c`, `z_score`, `current_id` y `baseline_id`.
- **error_states:** Indicador/unidad incompatibles, regiones distintas, variante day/night mezclada, valores no finitos, valores fisicamente imposibles, configuracion invalida y baseline insuficiente fallan con `TemperatureAnomalyError` o devuelven `quality_flag="insufficient_history"`/`no_data` no concluyente segun contratos de entrada.
- **edge_cases:** Una anomalia positiva representa superficie mas caliente que baseline. Z-score se calcula solo si `stddev > zscore_epsilon`; si no, queda `None` con motivo estable. Day y night no se mezclan salvo configuracion explicita `allow_variant_mismatch=True`, que queda solo para tests controlados.
- **auth_secrets:** Sprint 12 no introduce secretos ni llamadas remotas obligatorias. Consume observaciones LST y adaptadores fake. Si el smoke aplica datos reales, se usaran credenciales GEE prod-like sin imprimir secretos segun ADR vigente.
- **external_contracts:** Contrato publico en `mwangaza.data.temperature_anomaly`: `LstClimatologyConfig`, `LstYearObservation`, `LstClimatologyAdapter`, `TemperatureAnomalyConfig`, `TemperatureAnomalyError`, `compute_lst_climatology(...) -> Baseline` y `compute_temperature_anomaly(current, baseline, *, config=None) -> Anomaly`.
- **ui_states:** No hay UI nueva. Metadata deja estados listos para mostrar calor superior/inferior a baseline y no concluyente, sin recomendaciones ni score final.
- **rollback_compat:** Mantiene Sprints 0-11. No cambia API de `mwangaza.data.lst`, NDVI, lluvia ni contratos existentes. Reutiliza `Baseline` y `Anomaly`.
- **tests:** Tests bajo `tests/data/**` cubren climatologia LST, anomalia positiva/negativa en Celsius, z-score, historia insuficiente, propagacion de calidad, bloqueo de day/night mezclado, trazabilidad y ausencia de recomendaciones.


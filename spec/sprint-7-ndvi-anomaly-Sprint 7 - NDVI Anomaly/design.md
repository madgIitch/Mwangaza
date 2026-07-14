# sprint-7-ndvi-anomaly · undefined — Diseño

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

## Enfoque

- **data_model:** Retorna `Anomaly` NDVI con trazabilidad y valores derivados.
- **external_contracts:** `mwangaza.data.anomaly` con config explicita.
- **edge_cases:** Denominadores cercanos a cero, signo negativo y stddev insuficiente.
- **ui_states:** Sin UI nueva; distingue no disponible de cero.

## Decisiones de la entrevista

- **data_model:** Sprint 7 produce un `Anomaly` de Sprint 4 para `indicator="ndvi"` comparando una `IndicatorObservation` actual con un `Baseline` NDVI. El payload conserva `region_id`, `period_start`, `period_end`, `source`, `quality_flag`, `is_simulated`, `method`, `baseline_reference` y metadata con `current_id`, `baseline_id`, `absolute_anomaly`, `percent_anomaly`, `z_score`, `epsilon`, `baseline_mean` y `current_value`.
- **error_states:** Indicador no NDVI, unidades incompatibles, regiones distintas, periodos invertidos, baseline sin media usable, observacion actual sin valor usable o valores no finitos fallan con `NdviAnomalyError` o devuelven un `Anomaly` con `quality_flag` no concluyente segun el caso. La anomalia porcentual se omite con `None` cuando `abs(baseline.mean) <= epsilon`.
- **edge_cases:** La anomalia absoluta se calcula como `current.value - baseline.mean`, por lo que valores negativos indican vegetacion inferior al baseline. La anomalia porcentual usa `(current.value - baseline.mean) / baseline.mean * 100` solo si el denominador supera `epsilon`. El z-score se calcula solo si `baseline.stddev` existe y es mayor que `epsilon`; si no, queda `None` sin fallar.
- **auth_secrets:** Sprint 7 no introduce secretos, credenciales ni llamadas remotas. El calculo opera solo sobre contratos ya construidos y tests con fixtures/fakes locales.
- **external_contracts:** Contrato publico en `mwangaza.data.anomaly`: `NdviAnomalyConfig`, `NdviAnomalyError` y `compute_ndvi_anomaly(current: IndicatorObservation, baseline: Baseline, *, config: NdviAnomalyConfig | None = None) -> Anomaly`. La configuracion incluye `percent_epsilon` y `zscore_epsilon` con defaults seguros. No se codifican umbrales de alerta ni severidades.
- **ui_states:** No hay UI nueva. El payload deja listos valores y metadata para que UI futura pueda mostrar anomalia absoluta, porcentaje omitido por denominador pequeno y z-score no disponible sin confundirlos con cero.
- **rollback_compat:** No se rompen Sprints 0-6. Se reutilizan contratos de Sprint 4, observaciones de Sprint 5 y baselines de Sprint 6. No se cambian firmas publicas existentes ni se agregan dependencias pesadas.
- **tests:** Tests bajo `tests/data/**` cubren anomalia absoluta, porcentaje seguro con epsilon, signo negativo para vegetacion inferior, trazabilidad `current_id`/`baseline_id`, propagacion de calidad, z-score opcional, rechazo de indicadores/unidades/regiones incompatibles y ausencia de umbrales de alerta en el calculo.


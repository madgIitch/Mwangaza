# sprint-4-data-contracts · undefined — Diseño

## Scope (archivos que puede tocar)

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

## Decisiones de la entrevista

- **data_model:** Sprint 4 define contratos Python inmutables y serializables bajo `mwangaza.contracts`: `IndicatorObservation`, `Baseline`, `Anomaly`, `RiskSnapshot`, `Alert` y `Forecast`. Todos los payloads incluyen `schema_version`, `region_id`, campos temporales ISO8601 (`period_start`, `period_end` cuando aplique), `source`, `quality_flag`, `is_simulated` y `metadata`. Los indicadores validos son `ndvi`, `rainfall_mm`, `lst_c`, `composite_score` y `exposure`. Las unidades canonicas son `index`, `mm`, `celsius`, `score` y `people_estimate`.
- **error_states:** La validacion falla con `ContractValidationError` para `region_id` inexistente, indicador desconocido, unidad incompatible, fechas invertidas, valores no finitos (`NaN`, `inf`, `-inf`), `quality_flag` desconocido, `schema_version` incompatible, datos simulados marcados como observados o payloads con campos obligatorios ausentes. Los mensajes deben indicar campo y motivo sin incluir datasets grandes.
- **edge_cases:** `value=None` solo se permite cuando `quality_flag` es `no_data`, `insufficient_history` o `invalid`; nunca para `quality_flag=ok`. `exposure` es estimacion y no puede etiquetarse como personas afectadas reales. `period_start` debe ser menor o igual que `period_end`; forecasts tienen `issue_time`, `target_period_start`, `target_period_end` y `horizon_days`. Anomalias pueden ser absolutas o porcentuales, pero deben declarar `method` y referencia a baseline.
- **auth_secrets:** Sprint 4 no introduce secretos ni credenciales. Los contratos no leen `.env`, Earth Engine ni servicios remotos. Cualquier origen externo se representa como texto saneado en `source`/`source_version`, no como token, email privado o ruta local sensible.
- **external_contracts:** Contrato publico: modulo `mwangaza.contracts` con dataclasses/enums, `to_dict`, `from_dict`, `validate`, `loads_payload`, `dumps_payload` y JSON Schemas versionados en `src/mwangaza/contracts/schemas/` o `docs/contracts.md`. La version inicial es `mwangaza.contracts.v1`. Los contratos deben aceptar region IDs del catalogo de Sprint 3 mediante frontera inyectable o funcion de validacion sin llamar red.
- **ui_states:** Sprint 4 no cambia UI visible. Los contratos dejan preparado que UI/API distingan observados, simulados, cacheados y forecast por `is_simulated`, `source`, `quality_flag` y tipo de payload. Ningun payload simulado debe poder renderizarse como observado por falta de campo.
- **rollback_compat:** No se rompen Sprints 0-3: comandos `make lint/typecheck/test`, `/health`, GEE auth y `mwangaza.regions` siguen importables. No se añaden dependencias pesadas obligatorias; se prefiere stdlib/dataclasses. Los nombres de indicadores y `region_id` se alinean con Sprint 3.
- **tests:** Tests bajo `tests/contracts/**` cubren serializacion/deserializacion sin perdida, rechazo de no finitos, unidad incompatible, fechas invertidas, region inexistente, `is_simulated` obligatorio para fixtures simuladas, `schema_version` obligatorio, `quality_flag` con `value=None`, y roundtrip de fixtures canonicas para cada tipo de payload. Tests sin red ni Earth Engine.


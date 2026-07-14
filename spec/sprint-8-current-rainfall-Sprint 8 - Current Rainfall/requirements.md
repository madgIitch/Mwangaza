# sprint-8-current-rainfall · undefined — Requisitos

- name: `Sprint 8 - Current Rainfall` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T17:18:53.971Z

## Contexto



## Requisitos funcionales

R1. `compute_current_rainfall(...)` devuelve un `IndicatorObservation` valido con `indicator="rainfall_mm"`, `unit="mm"` y `value` igual a la precipitacion acumulada del periodo en milimetros.
R2. El resultado incluye en metadata `expected_days`, `available_days`, `missing_days` y `coverage_fraction`, con conteos coherentes y no negativos.
R3. Si `missing_days` supera `max_missing_days`, el resultado conserva el acumulado disponible pero usa `quality_flag="degraded"` y `metadata.incomplete_period=true`.
R4. Una region o periodo sin datos validos devuelve `value=None`, `quality_flag="no_data"` y no se representa como lluvia cero.
R5. Las fechas se interpretan en UTC ISO8601 y los dias esperados se calculan de forma inclusiva por fecha calendario UTC.
R6. La funcion rechaza resultados del adaptador cuyo periodo efectivo no coincide con el periodo solicitado, para no mezclar acumulados de periodos diferentes.
R7. `MWANGAZA_RAINFALL_COLLECTION` configura la coleccion de lluvia y por defecto usa un identificador CHIRPS documentado.
R8. Los tests usan adaptadores fake, no llaman Earth Engine ni servicios remotos, y cubren acumulado, periodo incompleto, no data, UTC y rechazo de periodos mezclados.

## Restricciones

- **error_states:** Errores controlados, `degraded` para periodo incompleto y `no_data` sin inventar cero.
- **auth_secrets:** Sin secretos ni red.
- **rollback_compat:** Mantiene Sprints 0-7 y variables existentes.


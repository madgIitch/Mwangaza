# sprint-8-current-rainfall · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) `compute_current_rainfall(...)` devuelve un `IndicatorObservation` valido con `indicator="rainfall_mm"`, `unit="mm"` y `value` igual a la precipitacion acumulada del periodo en milimetros.  ↔ R1
- [ ] (T2) El resultado incluye en metadata `expected_days`, `available_days`, `missing_days` y `coverage_fraction`, con conteos coherentes y no negativos.  ↔ R2
- [ ] (T3) Si `missing_days` supera `max_missing_days`, el resultado conserva el acumulado disponible pero usa `quality_flag="degraded"` y `metadata.incomplete_period=true`.  ↔ R3
- [ ] (T4) Una region o periodo sin datos validos devuelve `value=None`, `quality_flag="no_data"` y no se representa como lluvia cero.  ↔ R4
- [ ] (T5) Las fechas se interpretan en UTC ISO8601 y los dias esperados se calculan de forma inclusiva por fecha calendario UTC.  ↔ R5
- [ ] (T6) La funcion rechaza resultados del adaptador cuyo periodo efectivo no coincide con el periodo solicitado, para no mezclar acumulados de periodos diferentes.  ↔ R6
- [ ] (T7) `MWANGAZA_RAINFALL_COLLECTION` configura la coleccion de lluvia y por defecto usa un identificador CHIRPS documentado.  ↔ R7
- [ ] (T8) Los tests usan adaptadores fake, no llaman Earth Engine ni servicios remotos, y cubren acumulado, periodo incompleto, no data, UTC y rechazo de periodos mezclados.  ↔ R8
- [ ] Tests que cubran los criterios de aceptación

# sprint-11-current-land-surface-temperature - Sprint 11 - Current Land Surface Temperature - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_current_lst(...)` devuelve un `IndicatorObservation` con `indicator="lst_c"`, `unit="celsius"` y `value` igual a la media regional Celsius del periodo. -> R1
- [x] (T2) `summarize_lst_raw_values(...)` aisla la conversion `raw * scale + offset - 273.15` y los tests verifican la conversion de unidades. -> R2
- [x] (T3) Los pixeles marcados sin calidad no participan en media, mediana ni cobertura de pixeles validos. -> R3
- [x] (T4) La metadata incluye `mean_c`, `median_c`, `valid_pixel_count`, `total_pixel_count`, `coverage_fraction`, `actual_period_start` y `actual_period_end`. -> R4
- [x] (T5) Valores agregados fuera del rango fisico configurable se devuelven con `quality_flag="invalid"` y `value=None`, sin presentarlos como Celsius valido. -> R5
- [x] (T6) Una region o periodo sin pixeles validos devuelve `value=None`, `quality_flag="no_data"` y no se representa como cero. -> R6
- [x] (T7) La funcion rechaza resultados del adaptador cuyo periodo efectivo no coincide con el periodo solicitado. -> R7
- [x] (T8) Tests usan adaptadores fake, no llaman Earth Engine ni servicios remotos, y cubren conversion, mascara, estadisticos, cobertura, invalidos y no data. -> R8
- [x] Tests que cubran los criterios de aceptacion

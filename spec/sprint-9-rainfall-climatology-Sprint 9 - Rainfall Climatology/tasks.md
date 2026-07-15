# sprint-9-rainfall-climatology - Sprint 9 - Rainfall Climatology - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_rainfall_climatology(...)` devuelve un baseline de lluvia en `mm` con `mean`, `median`, `percentile_20`, `percentile_50`, `percentile_80` y `stddev` calculados sobre anos historicos incluidos. -> R1
- [x] (T2) Los anos cuya cobertura efectiva no alcanza `min_coverage_fraction` se excluyen, quedan en `excluded_years` con motivo estable y no participan en las estadisticas. -> R2
- [x] (T3) `min_years` es configurable; si los anos incluidos son menos que ese minimo, el baseline queda con calidad `insufficient_history`, estadisticas `None` y los motivos de exclusion preservados. -> R3
- [x] (T4) La unidad, indicador y acumulados historicos coinciden con `compute_current_rainfall(...)`: `indicator="rainfall_mm"` y `unit="mm"`. -> R4
- [x] (T5) `baseline_version` cambia de forma determinista cuando cambia la fuente de lluvia, la ventana objetivo, los anos incluidos o la configuracion de climatologia. -> R5
- [x] (T6) Los percentiles son deterministas y los tests cubren distribucion sesgada, valores extremos y muestras pequenas. -> R6
- [x] (T7) La ventana equivalente por ano usa fechas UTC inclusivas y no mezcla acumulados de periodos efectivos diferentes. -> R7
- [x] (T8) Los tests usan adaptadores fake, no llaman Earth Engine ni servicios remotos, y cubren estadisticas, exclusiones, historia insuficiente, versionado y edge cases temporales. -> R8
- [x] Tests que cubran los criterios de aceptacion

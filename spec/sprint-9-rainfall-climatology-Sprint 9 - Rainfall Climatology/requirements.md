# sprint-9-rainfall-climatology · undefined — Requisitos

- name: `Sprint 9 - Rainfall Climatology` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T12:10:51.796Z

## Contexto



## Requisitos funcionales

R1. `compute_rainfall_climatology(...)` devuelve un baseline de lluvia en `mm` con `mean`, `median`, `percentile_20`, `percentile_50`, `percentile_80` y `stddev` calculados sobre anos historicos incluidos.
R2. Los anos cuya cobertura efectiva no alcanza `min_coverage_fraction` se excluyen, quedan en `excluded_years` con motivo estable y no participan en las estadisticas.
R3. `min_years` es configurable; si los anos incluidos son menos que ese minimo, el baseline queda con calidad `insufficient_history`, estadisticas `None` y los motivos de exclusion preservados.
R4. La unidad, indicador y acumulados historicos coinciden con `compute_current_rainfall(...)`: `indicator="rainfall_mm"` y `unit="mm"`.
R5. `baseline_version` cambia de forma determinista cuando cambia la fuente de lluvia, la ventana objetivo, los anos incluidos o la configuracion de climatologia.
R6. Los percentiles son deterministas y los tests cubren distribucion sesgada, valores extremos y muestras pequenas.
R7. La ventana equivalente por ano usa fechas UTC inclusivas y no mezcla acumulados de periodos efectivos diferentes.
R8. Los tests usan adaptadores fake, no llaman Earth Engine ni servicios remotos, y cubren estadisticas, exclusiones, historia insuficiente, versionado y edge cases temporales.


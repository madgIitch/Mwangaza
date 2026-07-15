# sprint-10-rainfall-anomaly - Sprint 10 - Rainfall Anomaly - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_rainfall_anomaly(...)` devuelve un `Anomaly` con `indicator="rainfall_mm"`, `unit="mm"` y `value=current.value - baseline.mean`; un valor negativo representa deficit frente a la media. -> R1
- [x] (T2) `metadata.percent_anomaly` se calcula como porcentaje respecto a `baseline.mean` cuando la media supera `percent_epsilon`; si no, queda `None` con motivo estable. -> R2
- [x] (T3) `metadata.empirical_percentile` queda entre 0 y 100 y se calcula de forma determinista sobre valores historicos incluidos. -> R3
- [x] (T4) El calculo no inventa percentil cuando hay menos de `min_percentile_observations`; registra un motivo estable. -> R4
- [x] (T5) El resultado conserva referencia saneada a current y baseline mediante `current_id`, `baseline_id` y el campo contractual `baseline_id`. -> R5
- [x] (T6) La clasificacion tecnica usa exactamente `deficit_threshold_percent=-20.0` y `excess_threshold_percent=20.0` por defecto, pero no genera acciones, alertas ni severidad final. -> R6
- [x] (T7) La calidad mas restrictiva de current y baseline se propaga; `no_data` o `insufficient_history` producen valor no concluyente sin convertir ausencias en cero. -> R7
- [x] (T8) Tests cubren deficit, exceso, percentiles frontera, minimo de observaciones, trazabilidad, propagacion de calidad, umbrales internos documentados y ausencia de severidad/acciones. -> R8
- [x] Tests que cubran los criterios de aceptacion

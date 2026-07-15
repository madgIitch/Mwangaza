# sprint-10-rainfall-anomaly · undefined — Requisitos

- name: `Sprint 10 - Rainfall Anomaly` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T12:55:50.118Z

## Contexto



## Requisitos funcionales

R1. `compute_rainfall_anomaly(...)` devuelve un `Anomaly` con `indicator="rainfall_mm"`, `unit="mm"` y `value=current.value - baseline.mean`; un valor negativo representa deficit frente a la media.
R2. `metadata.percent_anomaly` se calcula como porcentaje respecto a `baseline.mean` cuando la media supera `percent_epsilon`; si no, queda `None` con motivo estable.
R3. `metadata.empirical_percentile` queda entre 0 y 100 y se calcula de forma determinista sobre valores historicos incluidos.
R4. El calculo no inventa percentil cuando hay menos de `min_percentile_observations`; registra un motivo estable.
R5. El resultado conserva referencia saneada a current y baseline mediante `current_id`, `baseline_id` y el campo contractual `baseline_id`.
R6. La clasificacion tecnica usa exactamente `deficit_threshold_percent=-20.0` y `excess_threshold_percent=20.0` por defecto, pero no genera acciones, alertas ni severidad final.
R7. La calidad mas restrictiva de current y baseline se propaga; `no_data` o `insufficient_history` producen valor no concluyente sin convertir ausencias en cero.
R8. Tests cubren deficit, exceso, percentiles frontera, minimo de observaciones, trazabilidad, propagacion de calidad, umbrales internos documentados y ausencia de severidad/acciones.


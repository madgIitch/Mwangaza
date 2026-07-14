# sprint-7-ndvi-anomaly · undefined — Requisitos

- name: `Sprint 7 - NDVI Anomaly` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T17:05:26.483Z

## Contexto



## Requisitos funcionales

R1. `compute_ndvi_anomaly(...)` devuelve un `Anomaly` valido para `indicator="ndvi"` cuya anomalia absoluta es exactamente `current.value - baseline.mean`.
R2. La anomalia porcentual se calcula como `(current.value - baseline.mean) / baseline.mean * 100` solo cuando `abs(baseline.mean)` supera `percent_epsilon`; si no, queda `None` y metadata registra el motivo.
R3. Un resultado absoluto negativo representa condiciones vegetativas inferiores al baseline y los tests cubren explicitamente ese signo.
R4. El resultado conserva en metadata identificadores o referencias estables `current_id` y `baseline_id` suficientes para trazabilidad.
R5. El `quality_flag` resultante propaga el estado mas restrictivo entre observacion actual y baseline; una observacion `no_data` o baseline `insufficient_history` no produce una anomalia concluyente.
R6. El z-score se calcula solo cuando `baseline.stddev` existe y supera `zscore_epsilon`; si no, queda `None` sin inventar variabilidad.
R7. La funcion rechaza indicadores, unidades o regiones incompatibles mediante `NdviAnomalyError` y no llama Earth Engine ni servicios remotos.
R8. El modulo no codifica umbrales de alerta, severidades ni recomendaciones de accion; solo devuelve valores de anomalia y trazabilidad.

## Restricciones

- **error_states:** Errores controlados y omision segura de porcentajes/z-score.
- **auth_secrets:** Sin secretos ni red.
- **rollback_compat:** Mantiene Sprints 0-6.


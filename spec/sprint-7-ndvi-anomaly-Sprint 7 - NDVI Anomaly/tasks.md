# sprint-7-ndvi-anomaly · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) `compute_ndvi_anomaly(...)` devuelve un `Anomaly` valido para `indicator="ndvi"` cuya anomalia absoluta es exactamente `current.value - baseline.mean`.  ↔ R1
- [ ] (T2) La anomalia porcentual se calcula como `(current.value - baseline.mean) / baseline.mean * 100` solo cuando `abs(baseline.mean)` supera `percent_epsilon`; si no, queda `None` y metadata registra el motivo.  ↔ R2
- [ ] (T3) Un resultado absoluto negativo representa condiciones vegetativas inferiores al baseline y los tests cubren explicitamente ese signo.  ↔ R3
- [ ] (T4) El resultado conserva en metadata identificadores o referencias estables `current_id` y `baseline_id` suficientes para trazabilidad.  ↔ R4
- [ ] (T5) El `quality_flag` resultante propaga el estado mas restrictivo entre observacion actual y baseline; una observacion `no_data` o baseline `insufficient_history` no produce una anomalia concluyente.  ↔ R5
- [ ] (T6) El z-score se calcula solo cuando `baseline.stddev` existe y supera `zscore_epsilon`; si no, queda `None` sin inventar variabilidad.  ↔ R6
- [ ] (T7) La funcion rechaza indicadores, unidades o regiones incompatibles mediante `NdviAnomalyError` y no llama Earth Engine ni servicios remotos.  ↔ R7
- [ ] (T8) El modulo no codifica umbrales de alerta, severidades ni recomendaciones de accion; solo devuelve valores de anomalia y trazabilidad.  ↔ R8
- [ ] Tests que cubran los criterios de aceptación

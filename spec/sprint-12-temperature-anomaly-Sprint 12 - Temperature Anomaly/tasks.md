# sprint-12-temperature-anomaly - Sprint 12 - Temperature Anomaly - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_lst_climatology(...)` devuelve un `Baseline` con `indicator="lst_c"`, `unit="celsius"`, estadisticos historicos y `quality_flag="insufficient_history"` cuando no alcanza `min_years`. -> R1
- [x] (T2) `compute_temperature_anomaly(...)` devuelve un `Anomaly` con `value=current.value - baseline.mean` expresado en grados Celsius. -> R2
- [x] (T3) Una anomalia positiva representa superficie mas caliente que el baseline y conserva `absolute_anomaly_c` en metadata. -> R3
- [x] (T4) `metadata.z_score` se calcula cuando `baseline.stddev > zscore_epsilon`; si no, queda `None` con motivo estable. -> R4
- [x] (T5) Los datos diurnos y nocturnos no se mezclan por defecto: `product_variant` de current y baseline debe coincidir. -> R5
- [x] (T6) El resultado conserva la variante del producto, `current_id`, `baseline_id` y `baseline_version` saneados. -> R6
- [x] (T7) `no_data` o `insufficient_history` producen valor no concluyente y propagan la calidad mas restrictiva sin convertir ausencias en cero. -> R7
- [x] (T8) El modulo no genera recomendaciones, acciones, alertas, severidad ni score final. -> R8
- [x] Tests que cubran los criterios de aceptacion

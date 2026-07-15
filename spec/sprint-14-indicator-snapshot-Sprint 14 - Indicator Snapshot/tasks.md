# sprint-14-indicator-snapshot · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) `build_indicator_snapshot(...)` devuelve un snapshot para una unica `region_id`, `period_start` y `period_end`, y rechaza senales de otra region o ventana incompatible.  ↔ R1
- [ ] (T2) El snapshot enumera indicadores presentes, ausentes y degradados usando las `quality_flag` contractuales sin convertir ausencias en cero.  ↔ R2
- [ ] (T3) El snapshot conserva las senales de entrada en una forma serializable estable y no recalcula ni consulta fuentes remotas.  ↔ R3
- [ ] (T4) Actualizar una fuente o cambiar cualquier payload crea un snapshot nuevo con `snapshot_id`/`content_hash` distinto, sin mutar snapshots previos.  ↔ R4
- [ ] (T5) `content_hash` es reproducible para el mismo contenido aunque el orden de entrada cambie.  ↔ R5
- [ ] (T6) `oldest_updated_at` y `newest_updated_at` se calculan desde `metadata.updated_at` cuando existe y usan `period_end` como fallback.  ↔ R6
- [ ] (T7) Payloads duplicados para el mismo indicador/tipo, indicadores desconocidos, unidades incompatibles, timestamps invalidos o contenido no serializable producen `IndicatorSnapshotError`.  ↔ R7
- [ ] (T8) La suite automatizada usa payloads locales/fakes sin llamadas remotas ni credenciales y cubre hash, calidad, fechas, inmutabilidad y rechazo de entradas incompatibles.  ↔ R8
- [ ] Tests que cubran los criterios de aceptación

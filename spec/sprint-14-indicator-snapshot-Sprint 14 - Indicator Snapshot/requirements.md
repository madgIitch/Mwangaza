# sprint-14-indicator-snapshot · undefined — Requisitos

- name: `Sprint 14 - Indicator Snapshot` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T15:50:16.842Z

## Contexto



## Requisitos funcionales

R1. `build_indicator_snapshot(...)` devuelve un snapshot para una unica `region_id`, `period_start` y `period_end`, y rechaza senales de otra region o ventana incompatible.
R2. El snapshot enumera indicadores presentes, ausentes y degradados usando las `quality_flag` contractuales sin convertir ausencias en cero.
R3. El snapshot conserva las senales de entrada en una forma serializable estable y no recalcula ni consulta fuentes remotas.
R4. Actualizar una fuente o cambiar cualquier payload crea un snapshot nuevo con `snapshot_id`/`content_hash` distinto, sin mutar snapshots previos.
R5. `content_hash` es reproducible para el mismo contenido aunque el orden de entrada cambie.
R6. `oldest_updated_at` y `newest_updated_at` se calculan desde `metadata.updated_at` cuando existe y usan `period_end` como fallback.
R7. Payloads duplicados para el mismo indicador/tipo, indicadores desconocidos, unidades incompatibles, timestamps invalidos o contenido no serializable producen `IndicatorSnapshotError`.
R8. La suite automatizada usa payloads locales/fakes sin llamadas remotas ni credenciales y cubre hash, calidad, fechas, inmutabilidad y rechazo de entradas incompatibles.


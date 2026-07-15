# sprint-13-spatial-aggregation · undefined — Requisitos

- name: `Sprint 13 - Spatial Aggregation` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T15:23:50.244Z

## Contexto



## Requisitos funcionales

R1. `aggregate_regions(...)` devuelve un resultado por cada `region_id` solicitado con `indicator`, `unit`, periodo, fuente, `quality_flag`, estadisticos y metadata de cobertura/trazabilidad.
R2. Cada agregado incluye media, mediana, percentiles configurables y area valida cuando la fuente lo permite; si la fuente no provee area, el campo queda explicitamente no disponible sin inventar cero.
R3. Regiones con `coverage_fraction` menor al umbral configurado quedan marcadas como no concluyentes o degradadas, preservando la cobertura observada.
R4. La agregacion usa la geometria analitica `geometry` del catalogo regional y nunca la `ui_geometry` simplificada.
R5. La configuracion impone limites de numero de regiones, escala y pixels remotos; excederlos falla antes de llamar al adapter.
R6. Los resultados se ordenan siempre por `region_id` y la misma entrada produce salidas estables dentro de una tolerancia numerica documentada.
R7. Indicadores o unidades desconocidas, regiones inexistentes, geometria vacia y valores no finitos producen errores controlados o calidad `invalid` sin respuestas parciales ambiguas.
R8. La suite automatizada usa adapters fake/mocks sin llamadas remotas ni credenciales reales y cubre calculo, cobertura, limites, geometria analitica y orden estable.


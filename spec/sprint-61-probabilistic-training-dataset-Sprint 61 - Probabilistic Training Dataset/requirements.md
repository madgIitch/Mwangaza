# sprint-61-probabilistic-training-dataset · undefined — Requisitos

- name: `Sprint 61 - Probabilistic Training Dataset` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-23T17:13:15.836Z

## Contexto



## Requisitos funcionales

R1. Cada fila se identifica por `region_id`, `as_of` UTC y `horizon_periods`; ninguna feature usa una observación posterior a `as_of`, demostrado con un sentinel futuro.
R2. Target binario exacto para orange/red, cero para green/yellow y null con reason code para unknown, calidad bloqueada, gap o futuro ausente.
R3. Horizontes 1-3 y features deterministas: actuales, lags 1-3, rolling 3/6, pendiente, delta, deterioro consecutivo, extremos/deficit y estacionalidad cíclica.
R4. Ventanas usan periodos contiguos; gaps, frecuencia mixta, región nueva e historia corta no se imputan silenciosamente.
R5. Cada fila conserva source, transformation, score, quality, geometry y threshold versions.
R6. Dataset expone schema/manifest, rango, regiones, frecuencia, conteos y SHA-256 estable sobre JSON canónico.
R7. Splits recomendados quedan definidos por fechas globales con gap por horizonte; el dataset no genera split aleatorio.
R8. Tests cubren leakage, gaps, duplicados, orden, timezone, no finitos, calidad, threshold_version y reproducibilidad.
R9. No se entrena modelo ni se añade endpoint o porcentaje.
R10. Documentación declara que las etiquetas son niveles Mwangaza, no verdad oficial independiente.

## Restricciones

- **error_states:** Errores bloqueantes y degradaciones por fila diferenciados.
- **auth_secrets:** Offline y metadata saneada.
- **rollback_compat:** Implementación aditiva.


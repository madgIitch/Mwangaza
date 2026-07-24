# Sesión actual

Feature: **sprint-61-probabilistic-training-dataset - Sprint 61 - Probabilistic Training Dataset** - estado: `review_pending`, spec aprobada.

## Resultado

- Dataset inmutable y determinista para frecuencias mensual/dekadal.
- Features actuales, lags 1-3, ventanas 3/6, pendientes, deltas, extremos, déficit, deterioro y estacionalidad.
- Targets exactos para horizontes 1-3 con null/reason codes y lineage versionado.
- JSON canónico, SHA-256 y escritura atómica.
- Sin entrenamiento, API pública o porcentaje.

## Validación

- 11 tests propios PASS.
- Regresión enfocada: 44 tests y 6 subtests PASS.
- Ruff enfocado PASS.

## Siguiente acción

- Revisar Sprint 61; al continuar, cerrarlo y preparar la spec de Sprint 62.

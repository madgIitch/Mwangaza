# Sesión actual

Feature: **sprint-62-calibrated-risk-classifier - Sprint 62 - Calibrated Risk Classifier** - estado: `review_pending`, spec aprobada.

## Resultado

- Persistencia, climatología estacional, frecuencia histórica, logística y histogram gradient boosting.
- Modelos compartidos para horizontes 10/20/30 días.
- Walk-forward global con gap, preprocessing por fold y regiones nuevas seguras.
- Selección por Brier OOF o abstención `rejected_insufficient_skill`.
- Manifiesto reproducible con hashes, versiones, parámetros y folds.
- Sin endpoint ni porcentaje público.

## Validación

- 16 tests probabilísticos PASS.
- Regresión enfocada: 49 tests y 6 subtests PASS.
- Ruff enfocado PASS.

## Siguiente acción

- Revisar Sprint 62; sólo tras aceptación preparar Sprint 63.

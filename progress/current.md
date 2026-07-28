# Sesión actual

Feature: **sprint-64-risk-probability-api-drivers — Sprint 64 - Drought Continuation API and Drivers** — estado: `review_pending`.

## Resultado

- Bundle hazard congelado con C=0.1 y 2.772 filas pre-2024 de 23 regiones.
- Run hash reproducible: `sha256:44c6ae469551ffdac0e11a73c9e47d3c4279dc0f1888bade434d4deca25b3070`.
- Snapshot: 92 resultados; 2 regiones activas con ML+referencia y 21 Normal como `not_applicable`.
- Endpoint GET dual a 30 días; baseline exclusivo a 60/90/180.
- ML siempre `inconclusive`, experimental y no operacional.
- Corrupción del modelo bloquea solo ML y no filtra paths.
- 126 tests de probabilístico/contratos/API/seguridad y gates oficiales pasan.

## Siguiente acción

- Mostrar endpoint y resultado real para revisión humana.
- Cerrar 64 si se acepta; no comenzar 65 antes de esa revisión.

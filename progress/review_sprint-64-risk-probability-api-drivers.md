# Sprint 64 · Revisión

Estado: `review_pending`.

- [x] Spec aprobado antes de implementar.
- [x] Fit final congelado y causal pre-2024.
- [x] Dos ejecuciones reales con hashes idénticos.
- [x] Snapshot real carga con manifiesto y bundle verificados.
- [x] ML y baseline simultáneos a 30 días; baseline solo en horizontes largos.
- [x] Corrupción de modelo deja ML unavailable y conserva referencia.
- [x] Ningún request entrena, escribe o llama GEE.
- [x] 126 tests enfocados/de regresión y 6 subtests pasan.
- [x] Gates oficiales de compile, unittest y diff-scope pasan.

Smoke real local: 23 resultados a 30 días, de los que `adm1-ke-20` y `adm1-ke-40`
están active/available con ambas estimaciones; las otras 21 regiones son `not_applicable`.

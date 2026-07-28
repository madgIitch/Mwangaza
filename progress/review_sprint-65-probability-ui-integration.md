# Sprint 65 · Revisión

Estado: `review_pending`.

- [x] Spec aprobado antes de implementar (`d0151e8`).
- [x] Selección exacta ADM1 sin herencia nacional o vecina.
- [x] ML y referencia simultáneos a 30 días.
- [x] Referencia exclusiva a 60/90/180 días.
- [x] ML inconcluso y no operacional visible.
- [x] `unavailable` conserva baseline y `not_applicable` no muestra 0%.
- [x] Drivers etiquetados como asociaciones no causales.
- [x] Low-bandwidth conserva método, skill, calidad y disclaimer.
- [x] Reportes conservan `as_of`, fase, artefacto, BSS, IC95 y abstención.
- [x] 59 tests frontend y 41 tests UI/reportes pasan.
- [x] Gate de modo impide cualquier mezcla entre fixtures y evidencia real.
- [x] Smoke real GEE Kenya: 47 ADM1 seleccionables y 121/121 payloads IGAD concluyentes.
- [x] Typecheck, lint y build de producción pasan.

Smoke local: el proxy devuelve 92 resultados, incluidos dos ADM1 activos a 30 días; el
PDF Kenya `RPT-KEN-A389F9FE3C` responde 200 y contiene 3.493 bytes.

La inspección visual automatizada no pudo ejecutarse porque esta sesión no expuso un
navegador. La revisión humana queda indicada en `progress/current.md`.

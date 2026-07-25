# Implementación · sprint-62c-adm1-antecedent-signals · Sprint 62C - ADM1 Antecedent Drought Signals

## 2026-07-25T15:43:09+02:00 — estado: review_pending

- Implementación manual sobre `main`, spec aprobado.
- Backfill ADM1 batched y reanudable con cinco fuentes, manifiesto geométrico y SHA-256.
- Preparación local anti-lookahead con SPI/déficits 1/3/6 y trayectoria NDVI.
- 27 tests probabilísticos y Ruff pasan.
- Smoke real Earth Engine: Turkana + Hiiraan, 2/2 filas, 0 señales ausentes.
- Gates configurados del harness: lint, typecheck, test y diff-scope pasan.
- Gates web adicionales: typecheck, lint y 49 tests pasan con pnpm 9.15.5.

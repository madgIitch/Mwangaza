# Sesión actual

Feature: **sprint-62f-drought-continuation-survival - Sprint 62F - Drought Continuation and Survival** — estado: `review_pending`, spec aprobada.

## Resultado

- 2.269 fases oficiales generan 192 episodios estrictos y 3.216 filas de risk set.
- Splits: 102 episodios train, 57 validación, 29 holdout y 4 purgados por frontera.
- Validación: `phase_survival` gana con IBS 0,179043; ambos ML quedan rechazados.
- Holdout abierto una vez: HGB obtiene IBS 0,265225 frente a 0,296562 del baseline.
- HGB reduce MAE de recuperación a 94,9 días, pero empeora Brier a 180 días y falla el gate.
- Hash validación: `sha256:26f1d6fd74a2873949fd2af2d42cedae3d4b7be2f84a8245316857b341c223cb`.
- Hash holdout: `sha256:8d0b592d380a77323329f2bc941819bc51fb305ae8e6ed631584d34e7f6ba955`.
- 248 tests del repositorio y 57 probabilísticos pasan; compilación y Ruff correctos.

## Siguiente acción

- Mostrar el resultado para revisión humana y cerrar formalmente 62F si se acepta.
- No reabrir ni usar el holdout 2024+ para ajustar este modelo.

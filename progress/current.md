# Sesión actual

Feature: **sprint-63-probability-calibration-skill-gate - Sprint 63 - Continuation Calibration and Hybrid Skill Gate** — estado: `review_pending`, spec aprobada.

## Resultado

- 2.955 filas causales pre-2024; ninguna fila del holdout usada.
- Tres folds anidados con 255 predicciones OOF de evaluación.
- `phase_survival`: Brier 0,195348 y ECE 0,098291.
- HGB: Brier 0,197150 y BSS -0,009222.
- HGB+Platt: Brier 0,249860, BSS -0,279051 y ECE 0,197380.
- ML falla por skill no positivo, calibración perjudicial y ECE superior a 0,15.
- Routing final: `phase_survival` a 30/60/90/180 días; no se genera bundle ML.
- Run hash: `sha256:5981338901de379c9943fd2f30b826d0ede687eccff5489657210476e4e74d39`.
- 66 tests probabilísticos, 248 tests del repositorio, compilación y Ruff pasan.

## Siguiente acción

- Mostrar el resultado para revisión humana y cerrar formalmente 63 si se acepta.
- Sprint 64 debe exponer el baseline con su método, no afirmar que procede de ML.

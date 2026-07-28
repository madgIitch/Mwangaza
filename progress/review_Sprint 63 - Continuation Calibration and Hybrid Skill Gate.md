# Review · Sprint 63

Estado: `review_pending`.

- [x] Spec aprobado antes de implementar.
- [x] Scope respetado.
- [x] Holdout 2024+ excluido de fitting, calibración y gates.
- [x] Folds base/calibración/evaluación disjuntos.
- [x] Gate y thresholds implementados sin reajuste posterior al resultado.
- [x] Routing ML/baseline/unavailable y soporte regional persistidos.
- [x] Artefacto ML solo se escribe si supera el gate.
- [x] 66 tests probabilísticos, 248 tests del repo, compilación y Ruff pasan.
- [ ] Aceptación humana antes de cerrar 63.

## Veredicto científico

HGB no supera `phase_survival` en la evaluación anidada y Platt empeora la probabilidad.
Los cuatro horizontes usan baseline; 64 no debe presentar ninguna salida como ML.

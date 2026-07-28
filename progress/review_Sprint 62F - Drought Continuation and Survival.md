# Review · Sprint 62F

Estado: `review_pending`.

- [x] Spec aprobado antes de implementar.
- [x] Scope respetado.
- [x] Risk set y targets causales con censura explícita.
- [x] Episodios disjuntos entre train, validación y holdout.
- [x] Holdout abierto una vez tras congelar código y hash de validación.
- [x] ML evaluado contra tres baselines y gate por horizonte.
- [x] Ablation de cinco familias solo sobre validación.
- [x] 248 tests, compilación y Ruff pasan.
- [ ] Aceptación humana antes de cerrar 62F.

## Veredicto científico

HGB muestra señal útil en holdout a 30-90 días y reduce el error de recuperación, pero
degrada 180 días. Queda `rejected`; no se habilita serving ni se retoca con el holdout.

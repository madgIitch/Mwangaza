# Sesión actual

Feature: **sprint-63b-ml-sanity-audit — Sprint 63B - Drought Continuation ML Sanity Audit** — estado: `review_pending`, spec aprobada.

## Resultado

- 2.955 filas causales pre-2024; 255 predicciones OOF y 29 episodios de evaluación.
- `phase_survival`: Brier ponderado por episodio 0,241388.
- HGB raw: 0,251157 (`no_skill`); Platt anual: 0,365766 (`no_skill`).
- Platt pooled: 0,237062, BSS +1,79% (`inconclusive`).
- Hazard logístico discreto: 0,203102, BSS +15,86%, ECE 0,108691 y 2/3 folds mejores.
- IC95 hazard-baseline: [-0,083941, +0,002149], por lo que no supera el gate robusto.
- Run hash: `sha256:2c2173803f14d7fa77e2d7b64d2742b4817a610ed8d57d4e22c396db2609d666`.

## Siguiente acción

- Mostrar el resultado para revisión humana.
- Si se acepta, cerrar 63B y aprobar 64 con baseline público; hazard permanece shadow.

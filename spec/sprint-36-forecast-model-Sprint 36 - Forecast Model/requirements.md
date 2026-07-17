# sprint-36-forecast-model · undefined — Requisitos

- name: `Sprint 36 - Forecast Model` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:48:17.591Z

## Contexto



## Requisitos funcionales

R1. El modelo por defecto es determinista, reproducible y no requiere GPU ni red.
R2. No se entrena si la serie tiene menos de cuatro puntos validos.
R3. El forecast incluye fecha de entrenamiento, horizonte, version e indicador.
R4. El backtest calcula MAE y error relativo seguro sin dividir por cero.
R5. La prevision se etiqueta como experimental y no sustituye a la observacion actual.
R6. Tests usan series fijas y no dependen de red.


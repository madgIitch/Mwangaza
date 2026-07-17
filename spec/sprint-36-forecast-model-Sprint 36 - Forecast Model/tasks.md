# sprint-36-forecast-model · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) El modelo por defecto es determinista, reproducible y no requiere GPU ni red.  ↔ R1
- [x] (T2) No se entrena si la serie tiene menos de cuatro puntos validos.  ↔ R2
- [x] (T3) El forecast incluye fecha de entrenamiento, horizonte, version e indicador.  ↔ R3
- [x] (T4) El backtest calcula MAE y error relativo seguro sin dividir por cero.  ↔ R4
- [x] (T5) La prevision se etiqueta como experimental y no sustituye a la observacion actual.  ↔ R5
- [x] (T6) Tests usan series fijas y no dependen de red.  ↔ R6
- [x] Tests que cubran los criterios de aceptación

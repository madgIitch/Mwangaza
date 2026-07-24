# sprint-62-calibrated-risk-classifier · undefined — Requisitos

- name: `Sprint 62 - Calibrated Risk Classifier` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-24T12:13:15.850Z

## Contexto



## Requisitos funcionales

R1. Entrena logística, histogram gradient boosting, persistencia, climatología estacional y frecuencia histórica para horizontes dekadales de 10/20/30 días.
R2. Walk-forward usa fechas globales y gap mínimo h; no existe shuffle/split aleatorio.
R3. Probabilidades finitas [0,1]; clase única o muestra insuficiente rechaza.
R4. Selección por Brier OOF con desempate determinista hacia modelo simple.
R5. ML sólo se selecciona si mejora persistencia y climatología; si no, rejected_insufficient_skill.
R6. Modelo regional compartido con categorías desconocidas seguras; sin modelos regionales individuales.
R7. Manifiesto conserva modelo, horizonte, dataset hash, manifest, thresholds, seed, parámetros, trained_until, folds y versiones.
R8. Misma entrada/config produce misma selección, probabilidades y hashes.
R9. Entrenamiento sólo offline/pipeline; ningún endpoint o path arbitrario.
R10. Tests cubren imbalance, región nueva, null, reproducibilidad, baselines, rechazo y ausencia de red/GEE.


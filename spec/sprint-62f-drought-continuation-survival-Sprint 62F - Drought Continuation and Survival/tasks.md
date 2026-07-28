# sprint-62f-drought-continuation-survival · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) El risk set contiene solo `as_of` dentro de episodios `drought_hazard_event` validados y conserva episodio, región, fecha, elapsed days, fase, tendencia, features e input hashes.  ↔ R1
- [x] (T2) Para 30/60/90/180 días, `same_episode_continues=1` exige que la fecha objetivo pertenezca al mismo episodio; vale 0 solo con Normal/Recovery validada tras su fin y antes o en la fecha objetivo; el resto es unknown/censored.  ↔ R2
- [x] (T3) Ninguna señal ni fase actual con `available_at`/`issued_at` posterior a `as_of` entra en features; los targets futuros nunca entran como predictor.  ↔ R3
- [x] (T4) Train usa episodios terminados antes de 2021; validación usa episodios con onset 2021-2023; episodios que cruzan el corte se purgan. El holdout usa onset 2024-2026 y permanece bloqueado salvo `--unlock-final-holdout`.  ↔ R4
- [x] (T5) Los candidatos always-active, supervivencia empírica condicionada por elapsed days, supervivencia por fase, logistic regression e HGB producen probabilidades sobre las mismas muestras conocidas y ningún `episode_id` aparece en dos splits.  ↔ R5
- [x] (T6) Las probabilidades 30/60/90/180 de cada muestra/candidato son monótonas no crecientes; cualquier ajuste monótono se aplica solo a predicciones y queda versionado.  ↔ R6
- [x] (T7) Se reportan Brier y log loss por horizonte, Brier integrado, calibration bins, recall de continuidad, precisión de recuperación, error de recuperación y denominadores/censura.  ↔ R7
- [x] (T8) ML solo queda `continuation_skill_eligible` si mejora estrictamente el Brier integrado del mejor baseline, no empeora ningún horizonte y reduce el error de recuperación con soporte mínimo de cinco episodios; en otro caso se abstiene con razón estructurada.  ↔ R8
- [x] (T9) Un ablation por familias (`rainfall_drought`, `vegetation`, `soil_water`, `atmospheric_demand`, `season_region`) usa únicamente validación y registra delta de Brier integrado; no se añade ninguna fuente nueva en este sprint.  ↔ R9
- [x] (T10) El CLI muestra ETA, escribe artefactos atómicos y hashes deterministas, impide abrir accidentalmente el holdout y los tests cubren causalidad, targets, censura, fronteras, monotonicidad, leakage, gates, ablation y reproducibilidad.  ↔ R10
- [x] Tests que cubran los criterios de aceptación

# Sprint 63 - Continuation Calibration and Hybrid Skill Gate — Implementación

- Folds anidados por episodios completos para 2021, 2022 y 2023.
- HGB base, calibrador Platt y evaluación temporalmente separados.
- Sentinel que bloquea filas y episodios desde 2024.
- Métricas Brier/BSS/log loss/bins/ECE y soporte explícito.
- Gate global y routing regional con fallback a `phase_survival`.
- Baselines monótonos por fase para 30/60/90/180 días.
- CLI offline con ETA, escrituras atómicas, hashes y manifiesto reproducible.

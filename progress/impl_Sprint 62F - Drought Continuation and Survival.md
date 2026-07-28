# Sprint 62F - Drought Continuation and Survival — Implementación

- Risk set causal dentro de fases activas validadas, con features, censura e input hashes.
- Targets de continuidad a 30/60/90/180 días; ausencia de recuperación validada queda unknown.
- Episodios estrictos separados por Normal, Recovery o huecos de cobertura.
- Splits por episodios completos con fronteras purgadas y holdout 2024+ sellado.
- Cinco candidatos, curvas monótonas, métricas de probabilidad/recuperación y ablation.
- CLI reproducible con ETA, escrituras atómicas y apertura única del holdout.

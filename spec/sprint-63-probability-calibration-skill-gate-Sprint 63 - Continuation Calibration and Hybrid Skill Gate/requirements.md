# sprint-63-probability-calibration-skill-gate · undefined — Requisitos

- name: `Sprint 63 - Continuation Calibration and Hybrid Skill Gate` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-28T13:59:56.884Z

## Contexto



## Requisitos funcionales

R1. El pipeline consume exclusivamente el risk set causal de episodios estrictos de 62F y el target `same_episode_continues`; onset, orange/red, impactos y targets censurados quedan fuera de fit y métricas.
R2. La evaluación genera folds 2021/2022/2023 por episodios completos: cada fold ajusta HGB antes del año de calibración, ajusta Platt solo con el año inmediatamente anterior y evalúa solo el año siguiente; episodios de frontera se purgan y ningún `episode_id` cruza particiones dentro del fold.
R3. Ningún archivo de predicciones o labels del holdout 2024+ se lee. Solo se admite el hash congelado `sha256:8d0b592d380a77323329f2bc941819bc51fb305ae8e6ed631584d34e7f6ba955` como evidencia, y un sentinel test hace fallar cualquier intento de usar fechas desde 2024 para fitting, calibración o gates.
R4. HGB+Platt solo puede producir la ruta `ml_experimental` a 30 días. Los horizontes 60/90/180 usan `phase_survival`, elegido en validación de 62F, y nunca quedan identificados como ML; 30 días también usa ese baseline cuando falla su gate.
R5. Para HGB sin calibrar, HGB+Platt y `phase_survival` se persisten Brier, BSS frente al baseline, log loss, cinco calibration bins fijos, ECE ponderado, filas conocidas, positivos, negativos, episodios y diagnóstico regional, con denominadores explícitos.
R6. El gate global de ML exige al menos 100 targets conocidos, 20 positivos, 20 negativos y 5 episodios de evaluación, BSS estrictamente positivo, Brier calibrado no peor que HGB sin calibrar, ECE menor o igual a 0,15 e inputs/hashes válidos. Cualquier fallo genera reason codes estables y activa fallback.
R7. Una región solo usa ML si sus predicciones OOF de 30 días contienen al menos un positivo y un negativo conocidos; en otro caso usa `phase_survival`. El baseline requiere al menos 20 targets conocidos y 5 episodios en el bucket de fase; si no, la ruta es unavailable.
R8. La decisión canónica por horizonte conserva `target`, `candidate`, `estimator_kind`, `experimental`, `fallback_reason`, métricas, soporte, versiones y hashes. El artefacto serializado de HGB+Platt solo se referencia cuando el gate global pasa; timestamp y paths absolutos no entran en el run hash.
R9. `scripts/calibrate_drought_continuation.py` es offline, muestra ETA, escribe config, OOF, routing, modelo y manifiesto de forma atómica bajo `data/models/drought-continuation/`; dos ejecuciones con los mismos inputs/config producen el mismo run hash.
R10. Tests cubren causalidad, folds anidados, censura, ausencia del holdout, calibración, métricas, thresholds, routing global/regional, fallback, artefactos corruptos, hashes y reproducibilidad; los gates del repo pasan.


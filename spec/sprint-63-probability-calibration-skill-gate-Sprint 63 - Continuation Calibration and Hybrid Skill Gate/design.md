# sprint-63-probability-calibration-skill-gate · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/calibrate_drought_continuation.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `config/probabilistic/**`
- `docs/probabilistic-risk.md`
- `docs/testing.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-63-probability-calibration-skill-gate-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** La entrada es el risk set estricto de 62F y el único target es
`same_episode_continues`. La salida es una decisión por horizonte con
`estimator_kind=ml|baseline|none`, candidato, probabilidad disponible, estado
experimental, métricas, soporte, reason codes y hashes. HGB solo compite a 30 días;
`phase_survival` cubre 60/90/180 y el fallback de 30.
- **error_states:** Se distinguen target censurado, clases/episodios insuficientes, calibración no
evaluable, BSS no positivo, región sin representación, calidad bloqueada, hash
incompatible y artefacto corrupto. ML no elegible degrada explícitamente a
`phase_survival`; si tampoco hay soporte baseline, queda unavailable. Nunca se usa 0.
- **edge_cases:** Los folds son temporales y por episodios completos. Para cada año de evaluación
2021, 2022 y 2023, el calibrador usa solo el año completo inmediatamente anterior y el
modelo base solo episodios terminados antes de ese año de calibración. Episodios que
cruzan una frontera se purgan. Unknown/censored no entra en fit ni métricas.
- **auth_secrets:** Flujo local y offline, sin red, credenciales ni secretos. Los datos/modelos
grandes permanecen bajo rutas ignoradas. El holdout 2024+ de 62F se identifica por su
hash únicamente como evidencia inmutable y ninguna ruta de datos holdout se abre.
- **external_contracts:** Se añade `scripts/calibrate_drought_continuation.py`. Consume features, fases y
episodios locales para reconstruir determinísticamente el risk set causal, más el
manifiesto congelado de validación 62F. Escribe config resuelta, métricas OOF, routing,
artefacto HGB+Platt de 30 días y manifiesto con hashes bajo
`data/models/drought-continuation/`.
- **ui_states:** Sin API o UI en este sprint. El CLI informa ETA y resume por horizonte si la ruta
es `ml_experimental`, `baseline` o `unavailable`, incluyendo fallback y razones. 64 y
65 consumirán el artefacto, pero no se implementan aquí.
- **rollback_compat:** Aditivo. No modifica 62F ni vuelve a abrir su holdout. Eliminar el nuevo directorio
de modelo restaura el estado anterior. No se publica ninguna probabilidad durante 63.
- **tests:** Tests offline cubren folds anidados, separación de episodios, censura, Platt,
BSS/ECE, thresholds exactos, routing, fallback regional, bloqueo del holdout, hashes,
determinismo y artefactos corruptos.


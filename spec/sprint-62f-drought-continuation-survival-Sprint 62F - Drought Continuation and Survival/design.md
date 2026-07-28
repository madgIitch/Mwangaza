# sprint-62f-drought-continuation-survival · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/evaluate_drought_survival.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `docs/probabilistic-risk.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62f-drought-continuation-survival-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Cada muestra parte de un `as_of` situado dentro de un episodio Alert/Alarm/Emergency
validado y conserva `episode_id`, elapsed days, fase/tendencia actual, señales causales,
horizonte y target `same_episode_continues`. El target vale 1 si el mismo episodio contiene
la fecha objetivo, 0 solo cuando existe recuperación Normal/Recovery validada entre ambos
momentos, y unknown en cualquier otro caso. Las curvas 30/60/90/180 son monótonas.
- **error_states:** Label actual no disponible en `as_of`, target sin cobertura, episodio right-censored,
recuperación no observada, soporte/clases insuficientes, curva no monótona, fuga entre
episodios, artefacto/hash inválido y holdout bloqueado tienen estados separados. Unknown
nunca se transforma en recuperación.
- **edge_cases:** Episodios que cruzan 2021 o 2024 se purgan de ambos lados del corte; uno simultáneo
en otra región es independiente. Un nuevo episodio tras recuperación no cuenta como
continuación del anterior. Left-censor permite continuidad futura pero no duración total;
right-censor solo aporta targets positivos observables dentro de su intervalo.
- **auth_secrets:** Sin red ni secretos. Solo se consumen features, labels y episodios locales enlazados
por SHA-256. Los artefactos grandes y predicciones quedan fuera de Git.
- **external_contracts:** Entradas versionadas de 62C/62D.2/62E. Salidas canónicas: risk set, predicciones
OOF, curvas, métricas, ablation y manifiesto. El holdout 2024-2026 requiere un flag de
desbloqueo y registra que se abrió; no se reajusta ninguna decisión después.
- **ui_states:** Sin UI ni serving. CLI con ETA y dos fases: desarrollo/validación por defecto y
apertura final explícita del holdout. El resumen muestra probabilidades por horizonte,
skill, recuperación y razones de abstención.
- **rollback_compat:** Aditivo; no modifica 62E ni habilita probabilidades públicas. Eliminar los nuevos
artefactos restaura el estado previo. Sprint 63 solo puede calibrar candidatos elegibles.
- **tests:** Tests offline cubren targets 1/0/unknown, recuperación entre episodios, censura,
episodios de frontera, disponibilidad temporal, monotonicidad, baselines, ablation,
determinismo y bloqueo/apertura única del holdout.


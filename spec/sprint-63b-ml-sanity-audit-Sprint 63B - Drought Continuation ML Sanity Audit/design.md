# sprint-63b-ml-sanity-audit · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/audit_drought_continuation_ml.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `config/probabilistic/**`
- `docs/probabilistic-risk.md`
- `docs/testing.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-63b-ml-sanity-audit-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Una muestra sigue siendo una fila causal de 62F con target 30 días. La unidad
estadística para pesos e incertidumbre es `episode_id`: todas las filas conocidas de un
episodio suman peso uno. Se comparan baseline, HGB raw/calibrado y hazard logístico.
- **error_states:** Se distinguen fold sin clases, calibración anual o pooled sin soporte, grid sin
fold válido, columna siempre missing, bootstrap no evaluable, fecha holdout, artefacto
corrupto y candidato sin skill. Cada caso genera reason codes y no inventa resultados.
- **edge_cases:** Tuning, calibración y evaluación se separan por años y episodios. Un episodio que
cruza una frontera se purga. Missingness se aprende en preprocessing. Bootstrap remuestrea
episodios completos, incluidos sus diferentes números de filas.
- **auth_secrets:** Auditoría offline, sin red ni nuevas fuentes. Datos/modelos grandes permanecen
ignorados. El holdout 2024+ no se lee ni se usa; un sentinel lo bloquea.
- **external_contracts:** CLI nuevo con config congelada. Consume los artefactos locales ya aprobados y
escribe selección por fold, OOF, métricas ponderadas/no ponderadas, bootstrap, veredicto
y manifiesto bajo `data/models/drought-continuation-ml-audit/`.
- **ui_states:** Sin API ni UI. El CLI muestra ETA y un veredicto `robust_skill`, `inconclusive` o
`no_skill`. No modifica routing de 63 ni habilita serving.
- **rollback_compat:** Aditivo y reversible eliminando los artefactos de auditoría. 63 queda como
evidencia congelada y 64 permanece pendiente hasta revisión humana de 63B.
- **tests:** Tests offline prueban pesos, indicadores de missingness, selección temporal,
calibración anual/pooled, hazard discreto, bootstrap por cluster, IC, sentinel y hashes.


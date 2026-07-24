# sprint-62-calibrated-risk-classifier · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `config/probabilistic/**`
- `data/models/.gitkeep`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `docs/probabilistic-risk.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62-calibrated-risk-classifier-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** `TrainingRun` registra resultados por horizonte, folds, candidatos y selección. Cada candidato guarda probabilidades OOF, Brier, seed, parámetros y versiones. El dataset añade `current_severe` para persistencia. El modelo regional compartido usa features numéricas y región categórica.
- **error_states:** Dataset/hash/schema incorrecto, horizonte ausente, features no finitas o fold inválido producen rechazo estable. Clase única, menos de 20 filas entrenables o menos de dos ejemplos por clase rechazan el candidato/horizonte. Ningún fallo crea probabilidad elegible.
- **edge_cases:** Walk-forward usa fechas dekadales globales ordenadas, al menos 36 periodos iniciales y gap de h índices temporales, equivalentes a horizontes 10/20/30 días. Regiones/categorías nuevas se codifican como desconocidas. Nulls se imputan por mediana aprendida sólo en train. Empate dentro de 1e-12 favorece persistencia, climatología, logística y boosting en ese orden.
- **auth_secrets:** Entrenamiento offline sin red/GEE. Artefactos son manifiestos JSON saneados; no se deserializan modelos desde input público ni se aceptan paths arbitrarios.
- **external_contracts:** scikit-learn `>=1.5,<2`. API Python `train_risk_candidates(dataset, config)`; no endpoint. Candidatos: Dummy/persistencia, climatología estacional, frecuencia histórica, LogisticRegression e HistGradientBoostingClassifier.
- **ui_states:** Sin UI. Diagnósticos usan `selected` o `rejected_insufficient_skill`.
- **rollback_compat:** Aditivo; no altera forecast 36/37. El campo `current_severe` es aditivo al manifest v1 y requiere bump a feature manifest v1.1.
- **tests:** Tests cubren folds globales/gap, reproducibilidad, probabilidades, baselines, clase única, nulls, región nueva, selección/rechazo y ausencia de shuffle/GEE.


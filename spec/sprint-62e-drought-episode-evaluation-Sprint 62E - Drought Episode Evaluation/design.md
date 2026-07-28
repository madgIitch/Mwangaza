# sprint-62e-drought-episode-evaluation · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/evaluate_drought_episodes.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `docs/probabilistic-risk.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62e-drought-episode-evaluation-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Mantener cuatro artefactos separados y enlazados por hash: observaciones NDMA
validadas, episodios reales, predicciones OOF por región/fecha/horizonte y evaluación
por episodio. Cada predicción conserva modelo, fold, `as_of`, fecha objetivo,
probabilidad, etiqueta conocida/unknown y `episode_id` cuando corresponda.
- **error_states:** Cobertura desconocida, periodo sin etiqueta oficial, episodio censurado,
horizonte sin folds elegibles, clase insuficiente, baseline ausente, predicción no
alineable y fuga de episodio son estados explícitos. Unknown nunca se convierte en
negativo y cualquier fuga invalida la corrida.
- **edge_cases:** Un episodio prolongado cuenta una sola vez; gaps de hasta 32 días conservan el
mismo episodio. Los episodios simultáneos de distintas regiones son independientes.
Onset de un episodio left-censored y recovery/duración de uno right-censored no entran
en la métrica correspondiente. Los episodios que tocarían dos folds se asignan
completos a uno y se purgan las filas fronterizas.
- **auth_secrets:** Sin red ni secretos. La evaluación consume únicamente artefactos locales
validados de features y NDMA/EM-DAT, conserva sus hashes y falla si faltan o no
coinciden con el manifiesto.
- **external_contracts:** Entradas: historial ADM1 de features, catálogo local `drought_hazard_event` y
episodios auditados de 62D.2. Salidas JSON/JSONL canónicas y deterministas con métricas
por candidato, horizonte, fold, región y episodio. Las etiquetas mensuales oficiales
se alinean con los dekads por su intervalo de validez; periodos sin observación son
unknown.
- **ui_states:** Sin UI. Un CLI reanudable muestra progreso y ETA, permite rutas explícitas y
produce resumen legible, predicciones OOF, episodios predichos, métricas y manifiesto.
- **rollback_compat:** Cambio aditivo. No modifica el entrenador v3 ni publica probabilidades. Borrar
los artefactos de evaluación restaura el comportamiento anterior. La decisión de 62E
es evidencia para 63, no una autorización de serving.
- **tests:** Fixtures offline cubren episodio largo, gap 32/33 días, splits globales,
purga de frontera, regiones simultáneas, unknown, censura, matching uno-a-uno,
falsas alarmas, onset/recovery/duración, determinismo y gate ML contra baselines.


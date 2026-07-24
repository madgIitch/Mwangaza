# sprint-61-probabilistic-training-dataset · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `config/probabilistic/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `docs/probabilistic-risk.md`
- `docs/contracts.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-61-probabilistic-training-dataset-*/**`
- `progress/**`

## Enfoque

- **data_model:** Contratos inmutables de entrada, fila, manifest y dataset.
- **external_contracts:** API Python y escritura atómica definidas.
- **edge_cases:** Frecuencia, gaps, ventanas, timestamps y targets exactos.
- **ui_states:** Sin UI; semántica documental explícita.

## Decisiones de la entrevista

- **data_model:** La entrada mínima es una secuencia de observaciones `HistoricalRiskPeriod` inmutables y ordenables por `region_id/as_of`, con frecuencia explícita, indicadores actuales opcionales, anomalías, score, nivel, quality, cobertura y versiones de lineage. La salida `TrainingDataset` contiene filas por región/as_of/horizonte, manifest, resumen y SHA-256 sobre JSON canónico. Features y target opcionales usan null, nunca sentinelas numéricos.
- **error_states:** Schema/frecuencia/horizonte inválidos, duplicados, timestamps no UTC, valores no finitos y versiones obligatorias ausentes bloquean el build con error estable. Historia corta, gaps o calidad no concluyente no bloquean el dataset: producen null y reason codes. Un target futuro desconocido/bloqueado es null.
- **edge_cases:** El builder ordena entrada desordenada, exige una sola frecuencia por build, detecta gaps por distancia temporal exacta, no salta huecos para fabricar lags y usa hasta seis periodos contiguos. Estacionalidad mensual usa mes; frecuencia dekadal usa posición 1..36. El periodo futuro debe caer exactamente a h pasos. Duplicados se rechazan.
- **auth_secrets:** Sprint offline, determinista y sin red/GEE. Lineage admite identificadores/versiones públicas, no credenciales, URLs firmadas o paths privados. La serialización se limita a metadata saneada y features.
- **external_contracts:** API Python bajo `mwangaza.probabilistic.dataset`: `build_training_dataset(observations, config)`, `canonical_dataset_json(dataset)` y `write_training_dataset(dataset, path)` con escritura atómica. No hay endpoint HTTP, entrenamiento ni integración UI.
- **ui_states:** Sin UI. La documentación explica que el target predice niveles del indicador Mwangaza y que null significa etiqueta no concluyente, no clase negativa.
- **rollback_compat:** Paquete aditivo que no altera contratos de forecast, risk, thresholds, cache o API existentes. El consumidor posterior lee schema/version/hash. Rollback por revertir el sprint.
- **tests:** Tests deterministas cubren tres horizontes, features temporales, estacionalidad, orden/hash, sentinel futuro anti-leakage, gaps, historia corta, target quality, threshold versions, timestamps, duplicados, valores no finitos y escritura atómica.


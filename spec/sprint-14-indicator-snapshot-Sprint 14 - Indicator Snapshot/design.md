# sprint-14-indicator-snapshot · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/data/**`
- `src/mwangaza/gee/**`
- `src/mwangaza/contracts/**`
- `tests/data/**`
- `tests/fixtures/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.github/workflows/**`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`
- `src/mwangaza/db/**`

## Decisiones de la entrevista

- **data_model:** Sprint 14 introduce un snapshot regional inmutable para una region y ventana de analisis. El snapshot agrupa senales ya calculadas (`IndicatorObservation`, `Anomaly`, `Baseline` si aplica) sin recalcular datos remotos. Debe exponer `snapshot_id`, `region_id`, `period_start`, `period_end`, indicadores presentes, ausentes y degradados, `oldest_updated_at`, `newest_updated_at`, `content_hash`, `is_simulated` y metadata de trazabilidad. No reemplaza aun `RiskSnapshot`.
- **error_states:** Region desconocida, ventanas incompatibles, indicadores duplicados, indicadores/unidades invalidos, payloads no contractuales, timestamps invalidos y contenido no serializable fallan con `IndicatorSnapshotError`. Observaciones `no_data`, `insufficient_history`, `invalid` o `degraded` se clasifican sin convertir ausencias en cero.
- **edge_cases:** Todas las senales deben pertenecer a la misma region y a la misma ventana exacta por defecto. El hash debe ser reproducible aunque cambie el orden de entrada. Actualizar una fuente crea un snapshot nuevo con hash distinto, nunca muta el anterior. La fecha mas antigua y mas reciente se calculan desde `metadata.updated_at` o, si falta, desde `period_end`.
- **auth_secrets:** Sprint 14 no introduce secretos ni llamadas remotas. Consume contratos ya calculados. Los snapshots y hashes no deben incluir rutas locales, secretos ni payloads de credenciales.
- **external_contracts:** Contrato publico previsto en `mwangaza.data.indicator_snapshot`: `IndicatorSnapshot`, `IndicatorSnapshotError`, `build_indicator_snapshot(...)` y helpers de serializacion. La entrada principal acepta una region, ventana y una secuencia de payloads contractuales o diccionarios contractuales ya saneados.
- **ui_states:** No hay UI nueva. El resultado deja datos listos para UI/API: indicadores presentes, ausentes y degradados; `oldest_updated_at` y `newest_updated_at`; y calidad agregada para distinguir datos completos, degradados y ausentes.
- **rollback_compat:** Mantiene Sprints 0-13. No cambia `IndicatorObservation`, `Baseline`, `Anomaly`, ni `RiskSnapshot`. El snapshot es modulo nuevo bajo `src/mwangaza/data/**` y no persiste en DB todavia.
- **tests:** Tests bajo `tests/data/**` cubren una region/ventana, rechazo de ventanas incompatibles, presentes/ausentes/degradados, hash reproducible, hash distinto al actualizar una fuente, fechas oldest/newest, no mutacion de snapshots previos, entrada como dict y ausencia de llamadas remotas.


# sprint-16-refresh-pipeline · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/pipeline/**`
- `src/mwangaza/cli.py`
- `tests/pipeline/**`
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

## Decisiones de la entrevista

- **data_model:** Sprint 16 introduce `PipelineRun`, `RegionRunResult`, `PipelineConfig` y `PipelineTask`. Cada run tiene `run_id`, `started_at`, `finished_at`, configuracion efectiva, resultado por region y resumen por estado (`cache_hit`, `remote_query`, `no_data`, `error`, `skipped`).
- **error_states:** Fallos regionales se capturan por region sin borrar resultados validos de otras regiones. Si los fallos superan `max_failure_fraction`, el run se marca fallido y el comando devuelve codigo no cero.
- **edge_cases:** `--resume` procesa solo unidades pendientes o fallidas segun resultados previos. La concurrencia maxima es configurable pero conservadora y validada. El orden de resultados es estable por region.
- **auth_secrets:** Sprint 16 no introduce secretos. La configuracion efectiva del run solo guarda valores saneados y nunca credenciales.
- **external_contracts:** Contrato publico en `mwangaza.pipeline`: `run_refresh_pipeline(...)`. CLI en `src/mwangaza/cli.py` expone `refresh-pipeline` y devuelve codigo 0/1 segun umbral de fallos.
- **ui_states:** No hay UI nueva. El resumen distingue cache hit, consulta remota, no_data y error para futura UI.
- **rollback_compat:** Mantiene `python -m mwangaza.data.refresh --dry-run` y no cambia contratos previos. Nuevo CLI es aditivo.
- **tests:** Tests bajo `tests/pipeline/**` cubren run_id, resume, fallo regional aislado, umbral de fallos, concurrencia validada y resumen de estados.


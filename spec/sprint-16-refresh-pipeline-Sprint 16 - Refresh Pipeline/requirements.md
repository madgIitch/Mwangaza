# sprint-16-refresh-pipeline · undefined — Requisitos

- name: `Sprint 16 - Refresh Pipeline` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T16:00:31.193Z

## Contexto



## Requisitos funcionales

R1. `run_refresh_pipeline(...)` crea un `PipelineRun` con `run_id`, `started_at`, `finished_at`, configuracion efectiva saneada y resultado por region.
R2. Un fallo regional produce resultado `error` solo para esa region y conserva resultados validos de otras regiones.
R3. `resume=True` procesa unicamente regiones pendientes o fallidas segun resultados previos.
R4. `max_concurrency` es configurable, positivo y limitado a un valor conservador.
R5. El run indica `exit_code=1` cuando la fraccion de fallos supera `max_failure_fraction`; en caso contrario `exit_code=0`.
R6. El resumen distingue `cache_hit`, `remote_query`, `no_data`, `error` y `skipped`.
R7. El CLI `mwangaza.cli refresh-pipeline` serializa el resumen y propaga el codigo de salida.
R8. La suite automatizada usa tareas fake sin llamadas remotas ni credenciales y cubre resume, fallos, resumen y CLI.


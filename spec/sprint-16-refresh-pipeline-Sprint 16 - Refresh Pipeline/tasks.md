# sprint-16-refresh-pipeline · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `run_refresh_pipeline(...)` crea un `PipelineRun` con `run_id`, `started_at`, `finished_at`, configuracion efectiva saneada y resultado por region.  ↔ R1
- [x] (T2) Un fallo regional produce resultado `error` solo para esa region y conserva resultados validos de otras regiones.  ↔ R2
- [x] (T3) `resume=True` procesa unicamente regiones pendientes o fallidas segun resultados previos.  ↔ R3
- [x] (T4) `max_concurrency` es configurable, positivo y limitado a un valor conservador.  ↔ R4
- [x] (T5) El run indica `exit_code=1` cuando la fraccion de fallos supera `max_failure_fraction`; en caso contrario `exit_code=0`.  ↔ R5
- [x] (T6) El resumen distingue `cache_hit`, `remote_query`, `no_data`, `error` y `skipped`.  ↔ R6
- [x] (T7) El CLI `mwangaza.cli refresh-pipeline` serializa el resumen y propaga el codigo de salida.  ↔ R7
- [x] (T8) La suite automatizada usa tareas fake sin llamadas remotas ni credenciales y cubre resume, fallos, resumen y CLI.  ↔ R8
- [x] Tests que cubran los criterios de aceptación

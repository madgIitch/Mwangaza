# sprint-13-spatial-aggregation · undefined — Diseño

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

## Decisiones de la entrevista

- **data_model:** Sprint 13 introduce agregados espaciales deterministas por region para indicadores ya existentes. El resultado publico sera una estructura serializable que conserva `region_id`, `indicator`, `unit`, periodo, fuente, `quality_flag`, estadisticos (`mean`, `median`, percentiles), cobertura (`valid_area`, `total_area`, `coverage_fraction`) y metadata de trazabilidad. No redefine `IndicatorObservation`, `Baseline` ni `Anomaly`.
- **error_states:** Region desconocida, geometria analitica vacia, indicador/unidad incompatible, limite de regiones excedido, escala invalida, cobertura insuficiente, pixels/datos ausentes y adapter remoto fallido se representan con excepciones controladas o `quality_flag` contractual. Una region sin cobertura suficiente nunca se representa como valor concluyente.
- **edge_cases:** Los resultados se ordenan por `region_id` para estabilidad. La geometria usada para analitica debe ser `geometry`, nunca `ui_geometry`. Percentiles solo se calculan cuando hay datos validos suficientes; valores no finitos se rechazan. Las tolerancias numericas de tests se documentan y no esconden cambios de unidades.
- **auth_secrets:** No se introducen nuevos secretos. La frontera GEE sigue usando la configuracion existente y las pruebas automatizadas usan adapters fake sin red ni credenciales. Si hay smoke real, se ejecuta con variables de entorno existentes y valida que no se imprimen secretos.
- **external_contracts:** Contrato publico previsto en `mwangaza.data.spatial_aggregation`: configuracion explicita, adapter mockeable, funcion para agregar una lista de regiones y resultado estable por region. El adapter debe aceptar geometria analitica, indicador, periodo, escala y limites, y devolver estadisticos/cobertura sin acoplar el dominio a Earth Engine real.
- **ui_states:** No hay UI nueva. Los agregados dejan estados listos para futuro mapa/tablas: ok, degraded, no_data, insufficient_coverage e invalid, con cobertura y fuente visibles para no confundir ausencia de datos con riesgo bajo.
- **rollback_compat:** Mantiene Sprints 0-12. No cambia contratos de NDVI, lluvia, LST, climatologias ni anomalias. Cualquier helper nuevo vive bajo `src/mwangaza/data/**` y usa contratos existentes cuando corresponda.
- **tests:** Tests bajo `tests/data/**` cubren orden estable, uso de `geometry` frente a `ui_geometry`, media/mediana/percentiles, cobertura insuficiente, limites de regiones/escala, rechazo de valores no finitos, errores controlados y ausencia de llamadas remotas.


# sprint-4-data-contracts · undefined — Requisitos

- name: `Sprint 4 - Data Contracts` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T14:30:47.176Z

## Contexto



## Requisitos funcionales

R1. `mwangaza.contracts` expone contratos versionados `IndicatorObservation`, `Baseline`, `Anomaly`, `RiskSnapshot`, `Alert` y `Forecast`, y cada payload serializado incluye `schema_version`.
R2. `IndicatorObservation` requiere `region_id`, `indicator`, `period_start`, `period_end`, `value`, `unit`, `source`, `quality_flag` e `is_simulated`; los indicadores validos son exactamente `ndvi`, `rainfall_mm`, `lst_c`, `composite_score` y `exposure`.
R3. La validacion rechaza valores no finitos, fechas invertidas, indicadores desconocidos, unidades incompatibles con el indicador, `region_id` inexistente y payloads sin campos obligatorios.
R4. Los datos simulados o fixtures canonicas incluyen `is_simulated=true`; un payload simulado no puede deserializarse como observado si falta o contradice ese campo.
R5. `value=None` solo es valido con `quality_flag` en `no_data`, `insufficient_history` o `invalid`; con `quality_flag=ok` se requiere un valor finito.
R6. Existen fixtures canonicas para cada tipo de contrato y los tests verifican que serializan y deserializan sin perdida, sin llamadas remotas ni Earth Engine.


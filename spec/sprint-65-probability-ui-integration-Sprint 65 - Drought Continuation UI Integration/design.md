# sprint-65-probability-ui-integration · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `src/mwangaza/contracts/**`
- `src/mwangaza/api/**`
- `src/mwangaza/services/**`
- `src/mwangaza/reports/**`
- `scripts/**drought*continuation*.py`
- `scripts/**adm1*.py`
- `config/probabilistic/**`
- `frontend/**`
- `tests/probabilistic/**`
- `tests/contracts/**`
- `tests/api/**`
- `tests/services/**`
- `tests/frontend/**`
- `tests/reports/**`
- `tests/security/**`
- `demo_data/**`
- `docs/probabilistic-risk.md`
- `docs/region-interface.md`
- `docs/reports-interface.md`
- `docs/contracts.md`
- `docs/public-api.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-65-probability-ui-integration-*/**`
- `progress/**`

## Enfoque

- **data_model:** target satelital, catálogo y cuatro horizontes definidos
- **external_contracts:** API, snapshot 121×4 y semántica de fuentes definidos
- **edge_cases:** disponibilidad temporal, histéresis y selección exacta definidos
- **ui_states:** consulta, observación, antigüedad y estados visibles definidos

## Decisiones de la entrevista

- **data_model:** El target pasa a ser `observed_drought_condition_continues`: continuidad de una
condición de sequía satelital homogénea, no continuidad de una fase administrativa. El
estado se deriva de familias independientes de señales GEE (meteorología, vegetación y
humedad del suelo) mediante una configuración versionada. Los 121 ADM1 producen cuatro
resultados, uno por horizonte. NDMA se conserva exclusivamente como validación externa.
- **error_states:** Toda ADM1 se evalúa. Si la condición no está activa devuelve `not_applicable` sin
porcentaje. Si está activa debe existir al menos una referencia histórica válida en cada
horizonte; una materialización real que deje una región activa sin probabilidad falla. La
calidad o ausencia de ML no oculta el baseline y nunca se sustituye un ausente por 0 %.
- **edge_cases:** La regla satelital usa solo señales cuyo `available_at` no sea posterior al
`as_of`, conserva `observed_at`, `available_at`, `age_days` y calidad por señal y aplica
límites de antigüedad versionados. Los episodios exigen dos dekads consecutivos de estrés
para activarse y dos dekads consecutivos sin estrés para cerrarse. Los límites nacionales,
selecciones sin ADM1 y regiones vecinas no heredan probabilidades.
- **auth_secrets:** Extracción/materialización son CLI explícitos y los secretos GEE no se serializan.
La API, el navegador y Reports solo leen artefactos verificados; no entrenan ni consultan
GEE durante una request. Los hashes, versiones y fechas de disponibilidad sí son trazables.
- **external_contracts:** El endpoint versionado mantiene filtros por `region_id`, `as_of` y horizontes
30/60/90/180. El snapshot real contiene exactamente el catálogo vigente de 121 ADM1 y
484 filas ordenadas. NDMA aporta métricas de concordancia externas donde exista; FEWS NET
permanece como `acute_food_insecurity_impact` y nunca crea estados ni episodios de sequía.
- **ui_states:** Region Explorer diferencia `query_generated_at`, `analysis_as_of` y fecha efectiva
de cada señal. `LIVE` describe la consulta, no la actualidad del dato. Una región activa
muestra probabilidad; una inactiva explica `not_applicable`. La vista normal,
low-bandwidth y Reports conservan target, horizonte, calidad, antigüedad y disclaimers.
- **rollback_compat:** El contrato anterior de fase oficial se conserva como evidencia/validación y no se
mezcla con el nuevo target satelital. El snapshot es versionado y reversible; un artefacto
inválido degrada solo continuidad sin contaminar el dashboard ni recurrir a fixtures demo.
- **tests:** Las pruebas bloqueantes cubren 121 ADM1 y 484 resultados, 47/47 Kenya, estado
activo/inactivo, probabilidades en cuatro horizontes, fechas y edades por señal, fuentes
asincrónicas, NDMA solo como validación, FEWS solo como impacto, hashes, API/UI/Reports y
walk-forward que impide usar features, estados o targets disponibles después del corte.


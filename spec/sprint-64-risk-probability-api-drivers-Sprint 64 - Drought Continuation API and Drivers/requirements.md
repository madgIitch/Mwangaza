# sprint-64-risk-probability-api-drivers · undefined — Requisitos

- name: `Sprint 64 - Drought Continuation API and Drivers` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-28T16:44:26.534Z

## Contexto



## Requisitos funcionales

R1. `GET /api/v1/drought-continuation-probabilities` acepta `region_id`, `as_of` y `horizon_days=30|60|90|180`, devuelve payload versionado y no inicia GEE, entrenamiento, calibración ni escritura.
R2. El contrato solo aplica cuando `current_drought_status=active`; en otro caso devuelve `not_applicable` y nunca interpreta ausencia de etiqueta como recuperación.
R3. Un resultado available incluye identidad, target `same_episode_continues`, fase, metadata, validation, quality y estimaciones tipadas con probability en `[0,1]`.
R4. A 30 días incluye simultáneamente `experimental_ml_prediction` del hazard congelado y `historical_reference` de `phase_survival`; nunca sustituye silenciosamente una por otra.
R5. ML conserva `validation_status=inconclusive`, `experimental=true`, `operational_use=false`, BSS, ECE, IC95 y folds de 63B; no afirma superioridad robusta ni validación operacional.
R6. A 60/90/180 días solo existe `historical_reference` y nunca se denomina predicción ML.
R7. Si hazard no es utilizable, ML queda unavailable con reason codes mientras la referencia válida puede seguir disponible; nunca se inventa un porcentaje.
R8. El contrato limita el claim a continuidad del mismo episodio y los drivers ML son asociativos; fase/elapsed del baseline son evidencia descriptiva.
R9. El fit final es CLI offline reproducible, usa configuración congelada de 63B, excluye 2024+, no retunea y serializa hashes/versiones; la API no entrena.
R10. La API verifica hashes de 63B; corrupción o falta de soporte invalida ML independientemente de la referencia.
R11. Paginación, orden, cache, errores y OpenAPI siguen patrones v1 y no filtran paths, secretos ni datos personales.
R12. Tests cubren comparación dual, cuatro horizontes, degradación independiente, drivers, hashes y ausencia de entrenamiento/GEE.


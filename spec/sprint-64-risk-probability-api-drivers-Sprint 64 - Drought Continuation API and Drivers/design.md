# sprint-64-risk-probability-api-drivers · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `src/mwangaza/contracts/**`
- `src/mwangaza/api/**`
- `src/mwangaza/services/**`
- `scripts/materialize_drought_continuation.py`
- `config/probabilistic/**`
- `tests/probabilistic/**`
- `tests/contracts/**`
- `tests/api/**`
- `tests/security/**`
- `tests/fixtures/probabilistic/**`
- `demo_data/**`
- `docs/probabilistic-risk.md`
- `docs/contracts.md`
- `docs/public-api.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-64-risk-probability-api-drivers-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** El resultado contiene una colección de estimaciones tipadas. A 30 días conviven
`experimental_ml_prediction` y `historical_reference`; a 60/90/180 solo existe la
referencia. Cada estimación tiene estado, probability opcional, método, evidencia y calidad.
- **error_states:** ML puede quedar unavailable sin ocultar una referencia válida. Se distinguen hash
incorrecto, artefacto corrupto, feature/region sin soporte, calidad bloqueada y drift. La
ausencia de sequía activa es `not_applicable`, nunca 0%.
- **edge_cases:** No se fusionan ni promedian ML y baseline. Una referencia no se denomina fallback
cuando se muestra simultáneamente. Targets censurados y cobertura desconocida no se
convierten en recuperación.
- **auth_secrets:** El fit/materializado es offline y sin red. El endpoint solo lee artefactos y
snapshots verificados; no inicia GEE, entrenamiento ni escrituras y no filtra paths.
- **external_contracts:** `GET /api/v1/drought-continuation-probabilities` admite filtros acotados por región,
fecha y horizonte. El hazard final usa exclusivamente configuración congelada de 63B y
datos pre-2024; hashes, versiones, BSS, ECE, folds e IC95 permanecen trazables.
- **ui_states:** Este sprint solo define API/servicio. El payload ML declara siempre
`validation_status=inconclusive`, `experimental=true` y `operational_use=false`; el copy
no afirma superioridad robusta. 65 será responsable de la presentación visual dual.
- **rollback_compat:** Contrato aditivo y versionado. Desactivar o retirar el artefacto hazard deja la
referencia histórica disponible y no cambia los endpoints previos.
- **tests:** Tests de dominio, contrato, API y seguridad cubren fit congelado pre-2024,
comparación dual, degradación independiente, horizontes largos, hashes, drivers y prueba
negativa de entrenamiento/GEE bajo request.


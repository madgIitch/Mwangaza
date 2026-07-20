# sprint-45-somalia-end-to-end-scenario · undefined — Diseño

## Scope (archivos que puede tocar)

- `tests/e2e/test_somalia_scenario.py`
- `tests/fixtures/scenarios/somalia/**`
- `scripts/demo_somalia.py`
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

- **data_model:** El escenario usa fixtures versionadas de Somalia con un `snapshot_id` estable, periodo, regiones, observaciones, calidad, score, alerta, recomendación, reporte y notificación simulada. Los artefactos derivados conservan el identificador del snapshot para trazabilidad.
- **error_states:** El comando falla con código distinto de cero y mensaje accionable si faltan fixtures, el snapshot es inválido o una etapa no produce su artefacto. Un fallo no deja una alerta o notificación parcial presentada como completada.
- **edge_cases:** La reejecución del mismo snapshot es idempotente; no duplica alertas ni notificaciones. `no_data` y calidad insuficiente se preservan como estados explícitos y nunca se convierten en valores favorables.
- **auth_secrets:** El recorrido offline usa adaptadores y fixtures locales, no requiere red, Earth Engine ni credenciales. Las notificaciones son exclusivamente simuladas y no contienen destinatarios reales.
- **external_contracts:** El entrypoint canónico es `python scripts/demo_somalia.py`; prepara y valida el estado completo usando contratos públicos existentes, produce un resumen verificable y admite repetición determinista sobre el mismo snapshot.
- **ui_states:** La demo expone mapa o su degradación accesible, tendencia, score, calidad, acción y reporte. Todo valor procedente de fixture se etiqueta como `demo` o `simulated`; los estados ausentes se muestran como no disponibles.
- **rollback_compat:** El escenario es aditivo y queda aislado en fixtures, script, tests y documentación. No cambia contratos productivos ni activa envíos o consultas remotas; retirarlo no invalida datos existentes.
- **tests:** Un test E2E offline verifica el recorrido completo, trazabilidad por snapshot, artefactos visibles, etiquetado simulado, código de salida y ausencia de duplicados al ejecutar dos veces.


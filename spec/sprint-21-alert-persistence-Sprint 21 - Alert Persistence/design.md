# sprint-21-alert-persistence · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/db/**`
- `src/mwangaza/alerts/repository.py`
- `tests/db/**`
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

- **data_model:** Sprint 21 introduce repositorio SQLite idempotente para alertas. Una alerta se identifica por region, tipo, periodo y version de modelo. Se guardan score, nivel, calidad, evidencias, recomendaciones, estado e historial de transiciones.
- **error_states:** Migraciones idempotentes, payload no serializable o claves incompletas producen `AlertRepositoryError`. Reprocesar el mismo snapshot actualiza/retorna la alerta existente sin duplicar.
- **edge_cases:** Cambio de severidad genera evento de transicion. Alertas resueltas conservan historia.
- **auth_secrets:** No guarda secretos ni credenciales.
- **external_contracts:** Contrato publico en `mwangaza.alerts.repository`: `AlertRepository`, `upsert_alert(...)`, `resolve_alert(...)`, `list_events(...)`.
- **ui_states:** Datos quedan consultables para UI/API posterior.
- **rollback_compat:** Aditivo bajo `src/mwangaza/db/**` y `src/mwangaza/alerts/repository.py`.
- **tests:** Tests bajo `tests/db/**` cubren migraciones, idempotencia, transiciones, resolucion e historial.


# sprint-20-early-action-recommendations · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/actions/**`
- `config/actions/**`
- `tests/actions/**`
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

- **data_model:** Sprint 20 introduce `ActionRecommendation` y catalogo editable por nivel. Cada recomendacion tiene accion, actor sugerido, urgencia, evidencia, `recommendation_version` y disclaimer prudente.
- **error_states:** Score no confiable o `unknown` produce recomendacion de revision de datos, no intervencion automatica. Catalogo incompleto o nivel invalido produce `RecommendationError`.
- **edge_cases:** Green monitoriza, yellow prepara, orange preposiciona, red activa urgente. Las recomendaciones no son ordenes oficiales ni consejo medico.
- **auth_secrets:** Sin secretos ni red.
- **external_contracts:** Contrato publico en `mwangaza.actions`: `recommend_actions(risk_snapshot, catalog=None)`.
- **ui_states:** Salida lista para UI con accion, actor, urgencia y evidencia.
- **rollback_compat:** No cambia RiskSnapshot ni alertas previas.
- **tests:** Tests bajo `tests/actions/**` cubren todos los niveles, unknown, catalogo editable, disclaimer y version.


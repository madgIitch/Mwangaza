# sprint-19-composite-drought-score · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/risk/**`
- `config/risk_models/**`
- `tests/risk/**`
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

- **data_model:** Sprint 19 introduce `RiskModelConfig`, `IndicatorContribution` y una funcion `compute_composite_drought_score(...)` que consume un snapshot y devuelve `RiskSnapshot`. El score queda 0-100, con contribuciones por NDVI, lluvia y LST, pesos y evidencia.
- **error_states:** Si faltan señales obligatorias o calidad bloqueada, el score es `None`, nivel `unknown` y `quality_flag` no concluyente. Pesos invalidos producen `RiskScoreError`.
- **edge_cases:** Si falta una señal opcional, los pesos se renormalizan y queda registrado. El mismo snapshot y version producen el mismo resultado.
- **auth_secrets:** Sin secretos ni red.
- **external_contracts:** Contrato publico en `mwangaza.risk`: `compute_composite_drought_score(snapshot, quality_report, config=None) -> RiskSnapshot`.
- **ui_states:** Resultado incluye contribuciones y evidencia para UI futura.
- **rollback_compat:** Usa `RiskSnapshot` existente sin cambiar contratos anteriores.
- **tests:** Tests bajo `tests/risk/**` cubren score 0-100, pesos, renormalizacion, obligatorio ausente, evidencia y determinismo.


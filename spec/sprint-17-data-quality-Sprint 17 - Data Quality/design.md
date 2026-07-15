# sprint-17-data-quality · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/quality/**`
- `tests/quality/**`
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

- **data_model:** Sprint 17 introduce `DataQualityReport`, `DataQualityRules` y contribuciones por dimension: frescura, cobertura espacial, cobertura temporal e historia suficiente. El score total queda entre 0 y 100 con desglose.
- **error_states:** Snapshots incompletos, timestamps invalidos o coverage fuera de rango producen `DataQualityError`. Calidad critica produce estado `data_review_required` y bloquea alertas automaticas.
- **edge_cases:** Datos disponibles no se ocultan aunque haya avisos. Ausencias y degradados reducen score. Reglas tienen `rules_version` estable y configuracion explicita.
- **auth_secrets:** Sin secretos ni red. Consume snapshots ya saneados.
- **external_contracts:** Contrato publico en `mwangaza.quality`: `evaluate_data_quality(snapshot, rules=None) -> DataQualityReport`.
- **ui_states:** El reporte incluye warnings y estado para mostrar avisos sin ocultar datos disponibles.
- **rollback_compat:** No cambia snapshots ni contratos previos. Modulo nuevo bajo `src/mwangaza/quality/**`.
- **tests:** Tests bajo `tests/quality/**` cubren snapshot completo, degradado, bloqueado, reglas versionadas y score 0-100.


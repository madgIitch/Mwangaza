# sprint-18-alert-thresholds · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/alerts/thresholds.py`
- `config/thresholds/**`
- `tests/alerts/test_thresholds.py`
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

- **data_model:** Sprint 18 introduce `ThresholdPreset`, `ThresholdBand` y `ThresholdClassification` con niveles `green`, `yellow`, `orange`, `red`, `unknown`, dominio cubierto sin solapes y `threshold_version`.
- **error_states:** Rangos solapados, huecos de dominio, limites invertidos, nivel invalido o valor no finito producen `ThresholdError`. Calidad bloqueada fuerza `unknown`.
- **edge_cases:** Los rangos son semiabiertos salvo el ultimo extremo superior inclusivo. Cambiar umbrales crea nueva version y no modifica clasificaciones anteriores.
- **auth_secrets:** Sin secretos ni red.
- **external_contracts:** Contrato publico en `mwangaza.alerts.thresholds`: `classify_value(...)`, `validate_preset(...)` y `default_threshold_preset()`.
- **ui_states:** Los presets se etiquetan como prototipo, no oficial IGAD, y `unknown` queda listo para UI.
- **rollback_compat:** No cambia alertas previas; modulo nuevo/aditivo.
- **tests:** Tests cubren niveles, cobertura de dominio, solapes, calidad bloqueada, version y preset prototipo.


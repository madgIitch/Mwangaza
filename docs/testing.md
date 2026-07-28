# Automated Testing

Mwangaza uses a layered, deterministic test suite. Automated tests do not require Earth Engine credentials, notification services or network access.

## Test groups

- `make test` runs the complete Python unit and integration suite.
- `make test-contract` runs domain JSON and public API contract tests; this group is merge-blocking in CI.
- `make test-frontend` runs the canonical React route smoke with demo fixtures.
- `make coverage` measures the critical backend modules configured in `pyproject.toml` and fails below 70%.
- `make quality-gate` combines backend, frontend, contracts, coverage and build checks.

CI exposes backend quality, backend tests, contracts/coverage and frontend smoke as separate jobs so failures identify the affected layer.

Shared deterministic helpers live in `tests/fixtures/deterministic.py`: a fixed UTC clock, queued fake Earth Engine responses and an in-memory simulated notifier. Existing focused tests cover no-data propagation, insufficient history, corrupt cache regeneration and retry/backoff without sleeping.

The Make targets force the test profile and clear inherited Earth Engine credential variables before execution. A developer's configured `.env` therefore cannot make unit, contract or coverage runs contact Earth Engine.

The frontend smoke opens `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin` and `/technical`, plus low-bandwidth mode. `app.py` remains covered only as a safe migration shim; React/Vite is the canonical UI.

Sprint 63 adds offline tests for nested temporal calibration, strict episode separation,
the pre-2024 sentinel, Platt fitting, Brier/BSS/ECE gates, phase-baseline support,
regional fallback, deterministic run hashes and corrupt model artifacts. The focused
suite is `uv run pytest tests/probabilistic/test_continuation_calibration.py -q`.

Sprint 63B añade pruebas de ponderación igual por episodio, indicadores de missingness,
selección HGB y hazard sin leakage temporal, Platt anual/pooled, bootstrap clusterizado,
sentinel 2024 y reproducibilidad. La suite enfocada es
`uv run pytest tests/probabilistic/test_ml_sanity_audit.py -q`; la regresión probabilística
completa es `uv run pytest tests/probabilistic -q`.

Sprint 64 añade pruebas de bundle congelado pre-2024, contrato dual, cuatro horizontes,
`not_applicable`, soporte/missingness/drift, drivers no causales, hashes corruptos con
baseline conservado, filtros/cache/OpenAPI y ausencia de fit/GEE bajo request. La suite
enfocada combina `test_continuation_serving.py`, `test_drought_continuation_contract.py`,
`test_drought_continuation_api.py` y `test_drought_continuation_security.py`.

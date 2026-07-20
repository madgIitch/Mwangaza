# Observability

Sprint 42 adds structured diagnostics for the API and the judge-facing technical panel at `/technical`.

## Correlation

Every HTTP request accepts an optional `X-Run-ID`. Valid identifiers are preserved; missing or invalid values are replaced. The same identifier appears in structured JSON events, API response headers and diagnostic payloads, including sanitized Earth Engine health failures.

## Endpoints

- `/health` is the existing liveness contract and now includes the current observability `run_id`.
- `/ready` checks the admin SQLite location and, when required, the cache directory. It returns HTTP 503 with sanitized check names if a required dependency is unavailable.
- `/api/v1/observability` returns readiness plus process-local aggregate counters for requests, duration, cache behavior, processed regions, errors and active alerts.

Set `MWANGAZA_CACHE_REQUIRED=true` when the deployment cannot serve without its configured `MWANGAZA_CACHE_DIR`. Metrics reset when the API process restarts and are intended for demo diagnostics, not long-term monitoring.

Logs are one JSON object per line. Recursive redaction replaces secret-like fields, known configured secret values and local paths. Full request or data payloads are not logged.

The `/technical` route is separate from the operational Overview and remains usable in low-bandwidth mode.

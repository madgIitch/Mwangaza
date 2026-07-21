# Public API

Sprint 33 adds read-only v1 endpoints:

- `/health`;
- `/api/v1/regions`;
- `/api/v1/snapshots/latest`;
- `/api/v1/alerts`;
- `/api/v1/alerts/{alert_id}`;
- `/api/v1/forecasts`;
- `/api/v1/reports/executive?region=<id>&period=<visible-period>`;
- `/api/v1/exports/snapshot?region=<id>&period=<visible-period>&format=csv|json`;
- `/openapi.json`.

All `/api/v1/**` responses include `schema_version="mwangaza.api.v1"`.
List endpoints use `items`, `limit`, `offset` and `total`, with a maximum limit
of 100.

By default, Public API requests do not start Earth Engine calculations or live
dashboard queries. Snapshot and alert responses use the safe dashboard/demo/export
contracts already available in process.

For prod-like local runs, set `MWANGAZA_API_DATA_MODE=live` before starting the
ASGI app. In that mode `/api/v1/snapshots/latest` and `/api/v1/alerts` use the
normal dashboard loader: live GEE first when credentials are configured, then
cache, then demo fallback. Responses still expose only sanitized export/API
payloads, never GEE secrets.

Errors use:

```json
{"error":{"code":"invalid_request","message":"limit must be an integer"}}
```

The generated OpenAPI JSON contains examples for the v1 endpoints.

Alert IDs are stable for a given observed alert payload and support direct,
sanitized detail routes. Report and export endpoints only accept the currently
materialized region/period context. They never initiate a browser-side or
download-time Earth Engine query. Downloads set a deterministic safe filename,
the correct MIME type and `Content-Disposition: attachment`; CSV/JSON omit UI
geometry by default and preserve missing values as null/empty contract values.

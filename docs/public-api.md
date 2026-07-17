# Public API

Sprint 33 adds read-only v1 endpoints:

- `/health`;
- `/api/v1/regions`;
- `/api/v1/snapshots/latest`;
- `/api/v1/alerts`;
- `/api/v1/forecasts`;
- `/openapi.json`.

All `/api/v1/**` responses include `schema_version="mwangaza.api.v1"`.
List endpoints use `items`, `limit`, `offset` and `total`, with a maximum limit
of 100.

Public API requests do not start Earth Engine calculations or live dashboard
queries. Snapshot and alert responses use the safe dashboard/demo/export
contracts already available in process.

Errors use:

```json
{"error":{"code":"invalid_request","message":"limit must be an integer"}}
```

The generated OpenAPI JSON contains examples for the v1 endpoints.

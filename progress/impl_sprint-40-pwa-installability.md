# Sprint 40 - React PWA Migration

Status: implemented; review pending.

Implemented:

- Approved the Sprint 40 spec through the harness using a manual interview because the external interview agent was unavailable.
- Added a React + Vite + TypeScript PWA under `frontend/`.
- Added manifest, icon and service worker shell caching that bypasses `/api/**` and `/health`.
- Migrated the operational dashboard surface to React: regional risk, region drilldown, active alerts, historical comparison, potential exposure, reports/export, forecast diagnostics, i18n and low-bandwidth table mode.
- Added API client usage for `/api/v1/snapshots/latest`, `/api/v1/alerts` and `/api/v1/forecasts`, with demo fixture fallback.
- Converted `app.py` into a Streamlit compatibility shim with a migration notice.
- Added frontend tests for render, low-bandwidth, i18n, offline shell, API contract consumption, manifest and service worker behavior.
- Added `MWANGAZA_API_DATA_MODE=live` so `/api/v1/snapshots/latest` and `/api/v1/alerts` can use the normal dashboard loader: live GEE, then cache, then demo fallback. The default remains demo to avoid accidental remote calls in local tests.
- Updated the React API client to populate metric cards from live/cache/demo snapshot rows returned by `/api/v1/snapshots/latest`.

Verification:

- `make lint`
- `make typecheck`
- `make test` (212 Python tests)
- `npm run lint`
- `npm run typecheck`
- `npm test` (8 frontend tests)
- `npm run build`
- `uv run python -m unittest tests.api.test_public_api` (7 tests)
- `make test` (212 Python tests)

# Admin Configuration

> Retired from the public frontend on 2026-07-29. `/admin`, its navigation item,
> screen, frontend types and frontend API client were removed. Existing backend admin
> contracts remain unchanged for compatibility; configuration is no longer exposed to
> judges through the canonical UI. The material below is retained as historical context.

Sprint 41 adds a demo-only admin panel at `/admin` backed by `/api/v1/admin/**`.

The panel versions threshold and early-action configuration. Saves are append-only: a new version is created with `version_id`, timestamp, actor, status, content hash, configuration snapshot and validation result. Invalid configuration is stored as rejected and never replaces the active version.

The hackathon panel is intentionally public and fully functional. Reading configuration, saving a new version and activating a valid version require no credentials or authorization headers.

This access model is only appropriate for the judge-facing demo. A production deployment must add identity provider integration, authorization policy, rate limiting and CSRF/session controls before exposing these mutation endpoints.

Operational notes:

- `MWANGAZA_ADMIN_DB` optionally selects the SQLite file for admin versions and audit records.
- Saving or activating configuration does not refresh Earth Engine, cache, forecasts or alerts.
- Rollback is manual: open `/admin`, choose a prior valid version from history, and activate it.
- The panel remains usable in low-bandwidth mode through forms and tables.

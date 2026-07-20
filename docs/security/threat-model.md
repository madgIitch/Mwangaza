# Threat Model

## Scope

Mwangaza is a hackathon prototype that combines public environmental data, local cache, SQLite state and a public React interface. It does not collect community names, phone numbers or individual locations.

## Assets and controls

| Asset or risk | Threat | Current control | Residual risk |
|---|---|---|---|
| Earth Engine credentials | Secret committed or emitted | Environment-only configuration, recursive log redaction and CI scanner | Host environment compromise remains out of scope |
| Indicator and alert data | Manipulated cache or admin rules | Validation, content hashes, append-only versions and audit events | The public demo admin permits intentional rule changes |
| Availability | Large bodies or request floods | 64 KiB body cap and process-local rate limit | Distributed attacks require a managed gateway |
| Public admin | Unauthorized configuration change | Explicit demo-only public access, validation, version history and rate limiting | Must gain institutional authentication before production |
| Desinformation | Prototype output presented as official | Source, mode, quality and prototype labels remain visible | Human communication can still omit context |
| Upload/traversal | Executable upload or filesystem escape | No upload contract; multipart and traversal-like request targets are rejected | Future upload features require a separate threat review |

## Trust boundaries

The browser, public API, Earth Engine, local cache and SQLite files are separate trust boundaries. External payloads must pass existing contracts before persistence or display. Logs and diagnostics expose identifiers and aggregates only.

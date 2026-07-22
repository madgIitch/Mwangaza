# Audit Trail

Sprint 34 adds append-only SQLite audit events through `AuditRepository`.

Each event includes actor, event type, entity type, entity id, region id,
timestamp, run id, snapshot id, model version and sanitized metadata.

Alert lifecycle helpers record separate events for:

- `alert_created`;
- `alert_escalated`;
- `alert_deescalated`;
- `alert_resolved`.

Configuration changes store previous and new versions with secret-like keys,
credentials, tokens and local paths redacted.

Queries can filter by `region_id`, `run_id` and `event_type`. There is no public
delete, truncate or purge method.

Sprint 59 adds `report_generated` and `report_downloaded` events for public report operations. They use actor `public-dashboard`, entity type `report`, stable report ID, region, run ID, snapshot ID and sanitized format/template metadata. Reading report lists or detail does not create audit events.

# Alert Persistence

Sprint 21 stores alert state and transitions in SQLite.

`AlertRepository` identifies an alert by region, alert type, period and model
version. Reprocessing the same snapshot updates the existing row instead of
creating duplicates. Severity changes create transition events, and resolved
alerts keep their event history.

Stored records include score, severity, quality flag, evidence metadata and
recommendations.

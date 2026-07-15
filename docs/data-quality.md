# Data Quality

Sprint 17 evaluates quality before later alert publication.

`evaluate_data_quality(snapshot, rules=None)` returns a `DataQualityReport` with a
0-100 score and contributions for freshness, spatial coverage, temporal coverage
and historical sufficiency. Critical quality sets
`status="data_review_required"` and `blocks_automatic_alerts=True`.

The report keeps available indicators visible and emits warnings such as
`stale_data`, `missing_indicators`, `degraded_indicators` and
`insufficient_history`.

Rules are configurable through `DataQualityRules` and carry a stable
`rules_version`.

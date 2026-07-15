# Indicator Snapshot

Sprint 14 creates immutable regional snapshots from already computed indicator
payloads.

Use `mwangaza.data.indicator_snapshot.build_indicator_snapshot(...)` with:

- one `region_id`
- one analysis window (`period_start`, `period_end`)
- contract payloads such as `IndicatorObservation`, `Anomaly` or their dict form
- optional `expected_indicators` to report missing signals

The builder does not call Earth Engine or recalculate indicators. It validates
that every signal belongs to the same region and exact window, classifies
indicators as present, absent or degraded using `quality_flag`, and computes a
stable SHA-256 `content_hash`.

`oldest_updated_at` and `newest_updated_at` come from `metadata.updated_at` when
available. If a signal has no update timestamp, its `period_end` is used as a
fallback.

Changing any signal creates a new `snapshot_id`/`content_hash`; previous snapshot
objects are immutable.

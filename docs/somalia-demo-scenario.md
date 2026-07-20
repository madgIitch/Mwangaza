# Somalia end-to-end demo scenario

Sprint 45 provides a deterministic offline scenario for the Bay pilot area in Somalia. It is a demonstration fixture, not a live operational assessment.

Run `python scripts/demo_somalia.py`. The command validates a versioned snapshot and writes `.demo/somalia-state.json` atomically. Its JSON summary links the accessible map fallback, trend, composite score, data quality, recommended action, report, persisted alert, and simulated notification to the same `snapshot_id`.

Re-running the command is idempotent: state is keyed by stable snapshot, alert, and notification identifiers. It performs no network requests, does not initialize Earth Engine, needs no credentials, and never sends a notification. Every fixture-derived artifact is explicitly marked `demo` or `simulated`.

For validation without changing the workspace, pass `--state /tmp/mwangaza-somalia-state.json`. Missing or malformed fixtures return a non-zero exit code and do not publish a completed state.

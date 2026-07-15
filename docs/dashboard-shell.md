# Dashboard shell

Sprint 22 replaces the foundation placeholder with the first operational Streamlit shell for Mwangaza.

## Contract

- `app.py` remains the Streamlit entrypoint.
- `mwangaza.ui.dashboard.render_dashboard()` renders the shell and catches loader failures.
- `mwangaza.ui.dashboard.build_dashboard_shell_html(...)` builds deterministic HTML/CSS for tests.
- `mwangaza.services.dashboard_shell.load_dashboard_shell_data(...)` first tries local materialized data and performs no remote reads.

## Visual model

The shell follows the approved visual reference without embedding the reference image:

- left navigation with `Overview`, `Region`, `Alerts`, `Reports` and `About`;
- top status bar with source, last update and freshness;
- regional map placeholder, active alerts, regional metrics and recommendations;
- compact white operational surfaces with green, yellow, orange and red risk accents.

## Data states

The UI labels origin modes as `live`, `cache` and `demo`. By default the loader scans the configured cache directory for already materialized `risk_snapshot`, indicator snapshot and indicator payload JSON. It also reads active alerts from the local SQLite alert database when present. If no materialized payload exists, it falls back to deterministic demo data labelled as `demo`.

Streamlit never starts Earth Engine work. Real observed values must be produced by the data/pipeline modules first and stored locally as cache or alert persistence artifacts.

Loader failures render a safe fallback shell. The fallback intentionally omits exception text, traceback, local paths and secret-like values.

## Layout

The CSS contract uses `overflow-x: hidden`, responsive `minmax(0, ...)` grid tracks, `min-width: 0` containment and a `1366px` max shell width to support 1366x768 without horizontal scroll.

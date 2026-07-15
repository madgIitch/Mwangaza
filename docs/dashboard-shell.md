# Dashboard shell

Sprint 22 replaces the foundation placeholder with the first operational Streamlit shell for Mwangaza.

## Contract

- `app.py` remains the Streamlit entrypoint.
- `mwangaza.ui.dashboard.render_dashboard()` renders the shell and catches loader failures.
- `mwangaza.ui.dashboard.build_dashboard_shell_html(...)` builds deterministic HTML/CSS for tests.
- `mwangaza.services.dashboard_shell.load_dashboard_shell_data(...)` returns demo shell data and performs no remote reads.

## Visual model

The shell follows the approved visual reference without embedding the reference image:

- left navigation with `Overview`, `Region`, `Alerts`, `Reports` and `About`;
- top status bar with source, last update and freshness;
- regional map placeholder, active alerts, regional metrics and recommendations;
- compact white operational surfaces with green, yellow, orange and red risk accents.

## Data states

The UI labels origin modes as `live`, `cache` and `demo`. Sprint 22 ships deterministic demo data only, but the chips are part of the public UI contract so future sprints can connect live and cached data without changing the shell language.

Loader failures render a safe fallback shell. The fallback intentionally omits exception text, traceback, local paths and secret-like values.

## Layout

The CSS contract uses `overflow-x: hidden`, responsive `minmax(0, ...)` grid tracks, `min-width: 0` containment and a `1366px` max shell width to support 1366x768 without horizontal scroll.

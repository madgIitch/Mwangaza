# Dashboard shell

Sprint 22 replaces the foundation placeholder with the first operational Streamlit shell for Mwangaza.

## Contract

- `app.py` remains the Streamlit entrypoint.
- `mwangaza.ui.dashboard.render_dashboard()` renders the shell and catches loader failures.
- `mwangaza.ui.dashboard.build_dashboard_shell_html(...)` builds deterministic HTML/CSS for tests.
- `mwangaza.services.dashboard_shell.load_dashboard_shell_data(...)` first tries local materialized data and performs no remote reads.

## Visual model

The shell follows the approved visual reference and the local `mwangaza-mockup/`
layout direction without embedding mock data or future-only interactions:

- top status bar with brand, source, last update and freshness;
- left navigation with `Overview`, `Region`, `Alerts`, `Reports` and `About`;
- regional risk choropleth, active alerts, regional metrics and recommendations;
- country drilldown and subnational pilot panel backed by loaded dashboard payloads;
- compact white operational surfaces with green, yellow, orange and red risk accents.

Mockup-only controls such as trend charts, CSV/JSON export, browser PDF generation,
language switching and low-bandwidth mode remain out of the active dashboard until
their own specs are approved.

## Data states

The UI labels origin modes as `live`, `cache` and `demo`. By default the loader first attempts a bounded Google Earth Engine live query when credentials are configured. If live GEE is unavailable, it scans the configured cache directory for already materialized `risk_snapshot`, indicator snapshot and indicator payload JSON. Risk snapshots feed the regional map; indicator payloads feed the metric cards. It also reads active alerts from the local SQLite alert database when present. If no live or materialized payload exists, it falls back to deterministic demo data labelled as `demo`.

Streamlit can start the bounded Sprint 23 Earth Engine live query for the configured dashboard region and period. It does not expose arbitrary geometry, collection, or date input to public users. Cache and demo remain the fallback paths.

Loader failures render a safe fallback shell. The fallback intentionally omits exception text, traceback, local paths and secret-like values.

## Layout

The CSS contract uses `overflow-x: hidden`, responsive `minmax(0, ...)` grid tracks, `min-width: 0` containment and a `1366px` max shell width to support 1366x768 without horizontal scroll.

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
- active alert filters by severity, country and region type, with the global
  active list kept separate from the selected region drilldown;
- temporal selector over already loaded snapshots; changing period updates map,
  metrics, alerts and recommendations client-side without recalculating GEE;
- indicator trend charts for NDVI, rainfall and LST, derived from loaded payload
  series and rendered with observed values, documented baseline line when
  available, explicit gaps and quality/anomaly details;
- historical comparison for the selected region, limited to same-window
  seasonal periods already present in live/cache/demo payloads;
- compact white operational surfaces with green, yellow, orange and red risk accents.

Mockup-only controls such as trend charts, CSV/JSON export, browser PDF generation,
language switching and low-bandwidth mode remain out of the active dashboard until
their own specs are approved.

## Data states

The UI labels origin modes as `live`, `cache` and `demo`. By default the loader first attempts a bounded Google Earth Engine live query when credentials are configured. If live GEE is unavailable, it scans the configured cache directory for already materialized `risk_snapshot`, indicator snapshot and indicator payload JSON. Risk snapshots feed the regional map; indicator payloads feed the metric cards. It also reads active alerts from the local SQLite alert database when present. If no live or materialized payload exists, it falls back to deterministic demo data labelled as `demo`.

Active alerts come from the SQLite `alerts` table with `status='active'` when
the database exists. The shell sorts them by severity, quality, latest period
and score, and each card shows summarized evidence plus the primary recommended
action. Resolved alerts are not rendered in the default active list. If SQLite
is unavailable, the shell derives the visible active alert from the loaded risk
payload while keeping the same labels and filters.

Streamlit can start the bounded Sprint 23 Earth Engine live query for the configured dashboard region and period. It does not expose arbitrary geometry, collection, or date input to public users. Cache and demo remain the fallback paths.

When multiple payload periods are loaded from cache or live output, the dashboard
groups them by `period_end`, selects the most recent period by default and marks
periods with incomplete signal coverage as `partial`. The browser-side period
selector only switches among those embedded cuts.

The historical comparison panel compares the current selected region with prior
payload periods only when the start and end month/day match exactly. Rows with
`no_data`, `insufficient_history` or non-numeric values are excluded. Users can
select up to three comparable periods in the browser; the current period remains
the reference. The narrative is intentionally limited to observed satellite
differences and does not infer causes, measured impacts or affected population.

Loader failures render a safe fallback shell. The fallback intentionally omits exception text, traceback, local paths and secret-like values.

## Layout

The CSS contract uses `overflow-x: hidden`, responsive `minmax(0, ...)` grid tracks, `min-width: 0` containment and a `1366px` max shell width to support 1366x768 without horizontal scroll.

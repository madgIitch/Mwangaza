# Regional risk map

Sprint 23 adds a deterministic IGAD choropleth map to the dashboard shell.

## Contract

- `mwangaza.maps.build_regional_risk_map(...)` builds a view model from local region catalog geometries and sanitized `RiskSnapshot` payloads.
- `mwangaza.maps.build_regional_risk_map_html(...)` renders deterministic SVG/HTML for Streamlit and tests.
- The dashboard consumes materialized local cache through `load_dashboard_shell_data(...)`; it does not call Earth Engine.
- `smoke_tests/sprint23_regional_risk_map_real_gee.py` is the opt-in real GEE smoke that authenticates with GEE and writes dashboard cache payloads.

## Visual states

Risk levels are shown as `green`, `yellow`, `orange`, `red` and `unknown`.
Regions without a valid risk snapshot, with non-finite score, or with blocking quality flags render as `unknown`, never as `green`.

Tooltips include region, score, risk level, period and quality. The map uses `ui_geometry` from the region catalog as WGS84 GeoJSON; analytical geometry remains separate.

## Smoke test

Run manually with GEE credentials already exported:

```bash
python smoke_tests/sprint23_regional_risk_map_real_gee.py --cache-dir .cache/mwangaza --region-id som
```

The script reads credentials only from environment variables, prints sanitized GEE status, validates generated payloads for secret-like fields/values, and writes cache entries consumed by the dashboard.

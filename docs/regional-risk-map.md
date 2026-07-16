# Regional risk map

Sprint 23 adds a deterministic IGAD choropleth map to the dashboard shell.

## Contract

- `mwangaza.maps.build_regional_risk_map(...)` builds a view model from local region catalog geometries and sanitized `RiskSnapshot` payloads.
- `mwangaza.maps.build_regional_risk_map_html(...)` renders deterministic SVG/HTML for Streamlit and tests.
- `mwangaza.services.live_gee_dashboard.load_live_gee_dashboard_payloads(...)` queries Earth Engine for NDVI, rainfall and LST, then builds the dashboard risk payloads.
- The dashboard calls GEE directly in `live` mode when credentials are configured, using the enabled IGAD countries from `MWANGAZA_ENABLED_COUNTRIES` and the latest common available date across the configured NDVI, rainfall and LST collections. If GEE is unavailable, it falls back to local cache and then demo data.
- Passing an explicit `region_id` keeps the live query scoped to that single bounded region for smoke tests and diagnostics.
- `smoke_tests/sprint23_regional_risk_map_real_gee.py` uses the same live GEE path and writes dashboard cache payloads for repeatable manual validation.

## Visual states

Risk levels are shown as `green`, `yellow`, `orange`, `red` and `unknown`.
Regions without a valid risk snapshot, with non-finite score, or with blocking quality flags render as `unknown`, never as `green`.

Tooltips include region, score, risk level, period and quality. The map uses `ui_geometry` from the region catalog as WGS84 GeoJSON; analytical geometry remains separate.

## Smoke test

Run manually with GEE credentials already exported:

```bash
python smoke_tests/sprint23_regional_risk_map_real_gee.py --cache-dir .cache/mwangaza --region-id som
```

The script reads credentials only from environment variables, queries real GEE datasets, prints sanitized GEE status, validates generated payloads for secret-like fields/values, and writes cache entries consumed by the dashboard.

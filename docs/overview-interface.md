# Overview Interface Target

`/overview` is the main operational situation screen for Mwangaza. It gives an analyst a fast regional read, connects that read to the selected region, and turns the current snapshot into actions, reports and exports.

## Visual Thesis

Bright operational cockpit: map-first, alert-aware, dense enough for repeated scanning, and restrained enough that severity colors carry meaning.

## Content Plan

1. Global shell: persistent brand, navigation, data source, last update, freshness, notification and account placeholders.
2. Situation layer: IGAD risk map and prioritized active alerts.
3. Regional comparison layer: all eight IGAD countries, including explicit unassessed states.
4. Selected-region layer: selected country/pilot drill-down, key indicators, exposure and data quality.
5. Evolution layer: NDVI and rainfall trends against baseline when payloads exist.
6. Action layer: early action recommendations, executive PDF report CTA, CSV/JSON export and responsible-use footer.

## Interaction Thesis

- Selecting a country from the map or selector updates the same already-loaded dashboard/API payload; the browser must not call Earth Engine directly.
- Sidebar entries are page routes, not hash anchors. `Overview` routes to `/overview`; alerts, reports, regions and about are independent pages.
- Low-bandwidth mode keeps the same operational information in tables and avoids heavy map/chart surfaces.

## Required Sections

### Global Header

- Left: Mwangaza mark, product name and tagline.
- Status strip:
  - Data source, currently derived from the loaded dashboard source.
  - Last update from the visible snapshot.
  - Freshness badge based on data mode/message.
- Right placeholders:
  - Notifications.
  - User avatar/account.

The implementation exposes source/update/freshness in the topbar. Notification and account states are explicitly labelled unavailable and are non-interactive until an approved identity/notification contract exists.

### Sidebar

Navigation items:

- Overview, active on `/overview` and `/` compatibility route.
- Regions, route `/region`.
- Active alerts, route `/alerts`.
- Reports and export, route `/reports`.
- About, route `/about`.

No sidebar label should use `#...` anchors or trigger autoscroll inside Overview.

### Language

Target language buttons: `EN`, `SW`, `SO`.

The operational selector exposes English, Kiswahili and Somali. Spanish remains available as a compatibility locale. Technical values, units and source identifiers are not translated.

### Low-Bandwidth Mode

The toggle simplifies maps/charts into tables while preserving:

- Key indicators.
- Active alerts.
- Recommendations.
- Report/export references.

### Risk Map - IGAD

Primary target: a choropleth over configured IGAD countries.

Severity colors:

- Green: low.
- Yellow: watch.
- Orange: alert.
- Red: severe.
- Gray: not assessed.

The map must never render a no-data region as green. If geometry is unavailable, it must show an explicit placeholder rather than invented shapes.

The map uses `react-simple-maps` with a lazily loaded, validated geoBoundaries ADM1 presentation atlas. ADM1 polygons are consolidated into one processed `uiGeometry` per IGAD country before rendering; API risk and quality are joined by stable country ID. This avoids analytic/GEE geometry in the browser, keeps unassessed countries gray and prevents boundary data from entering the low-bandwidth bundle. Home restores the IGAD frame, zoom is bounded to 1x-4x, and the layer selector switches between risk and data quality without another API or GEE request.

### Active Alerts

Shows the highest-priority active alerts, ranked by severity first.

Each alert should show:

- Rank.
- Region.
- Severity.
- Short reason/title.
- Period/date.
- `View details` route.

Active alerts use stable backend IDs. Detail links route to `/alerts/<alert_id>` and the global link preserves visible region, period and active status. Existing alerts expose evidence and action context; missing IDs render an accessible sanitized 404 state.

### Selected Region

Overview never reduces the situation view to the selected country. A persistent regional comparison lists all eight configured IGAD countries with score, severity, quality and active-alert count. Countries missing from the loaded snapshot remain visible as unassessed and cannot change the drill-down. Selecting an assessed country from the map, comparison band or selector updates the focused analysis below.

Shows:

- `Selected region: <name>`.
- Region selector.
- Key indicators for the selected profile.
- Data quality and potential exposure.

Changing the region updates indicator cards, trends, recommendations and report/export context from the loaded payload.

### Indicator Cards

Required cards:

- NDVI anomaly.
- Rainfall anomaly.
- Land Surface Temperature anomaly.
- Composite drought score.
- Data quality.
- Potentially exposed population.

Monthly comparisons should only appear when comparable snapshots exist. Current implementation shows compact `No comparison yet` placeholders where deltas are absent.

### Trends

Shows trends for the selected region. Target state compares current values against historical baseline using line charts.

Available 12-24 point `RegionProfile.trends` render as anomaly lines around a zero baseline with dates, scale, focusable points, tooltips and explicit gaps. Low-bandwidth mode provides equivalent tables. Missing trend payloads remain explicit placeholders.

### Early Action Recommendations

Recommendations are decision support, not official instructions. They should eventually include evidence, actor, priority and time horizon.

Current implementation reuses selected-profile recommendations from the loaded payload.

### Executive PDF Report

Target state: generate a PDF for the selected snapshot, including region, period, alert level, map, indicators, trends, quality, recommendations, sources, methodology and limitations.

The CTA downloads a real PDF response for the visible materialized region/period context. The API sets a deterministic filename, PDF MIME type and attachment disposition without running Earth Engine.

### Export Data

Target state: download CSV and JSON for the current view without secrets, tokens, local paths or unnecessary high-resolution geometries.

CSV and JSON actions download the visible materialized region/period context from real endpoints. Geometry is omitted by default and missing values remain explicit.

### Footer

Must state that Mwangaza is a decision-support prototype and should be used with local knowledge. Institutional logos must only be used with permission; otherwise use text attribution.

## Implemented Now

- `/overview` route renders the main operational cockpit.
- `/` remains a compatibility route for the same screen.
- Sidebar uses page routes, not hash anchors.
- Risk map uses processed UI-only boundary geometry and an explicit fallback when the validated atlas cannot load.
- Active alerts, selected-region indicators, trends, recommendations and report/export references use existing `DashboardData`.
- Legacy hash URLs are cleaned on mount to prevent autoscroll.

## Remaining Boundaries

- Notifications and accounts remain intentionally unavailable until their own approved contracts exist.
- Recommendations remain decision support; actor and time-horizon fields require a future structured action contract.
- Reports Center workflow changes remain outside this sprint; Overview only links its own context-bound downloads.

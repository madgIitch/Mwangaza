# Overview Interface Target

`/overview` is the main operational situation screen for Mwangaza. It gives an analyst a fast regional read, connects that read to the selected region, and turns the current snapshot into actions, reports and exports.

## Visual Thesis

Bright operational cockpit: map-first, alert-aware, dense enough for repeated scanning, and restrained enough that severity colors carry meaning.

## Content Plan

1. Global shell: persistent brand, navigation, data source, last update, freshness, notification and account placeholders.
2. Situation layer: IGAD risk map and prioritized active alerts.
3. Selected-region layer: selected country/pilot, key indicators, exposure and data quality.
4. Evolution layer: NDVI and rainfall trends against baseline when payloads exist.
5. Action layer: early action recommendations, executive PDF report CTA, CSV/JSON export and responsible-use footer.

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

Current implementation exposes source/update/freshness in the topbar. Notification and account controls are placeholders for a future sprint.

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

Current implementation supports English and Kiswahili plus the existing Spanish locale from earlier sprint work. Somali locale is pending and tracked for a future sprint.

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

Current implementation uses `react-simple-maps` and the same `ui_geometry` contract used by `/region`. Home, zoom and layer controls are visual placeholders until map viewport/layer state is implemented.

### Active Alerts

Shows the highest-priority active alerts, ranked by severity first.

Each alert should show:

- Rank.
- Region.
- Severity.
- Short reason/title.
- Period/date.
- `View details` route.

Current implementation uses active alerts from the dashboard/API payload. Dedicated alert detail pages and filtered alert center are pending.

### Selected Region

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

Current implementation reuses available `RegionProfile.trends` as compact bar-style trend previews. Missing trend payloads must remain explicit placeholders.

### Early Action Recommendations

Recommendations are decision support, not official instructions. They should eventually include evidence, actor, priority and time horizon.

Current implementation reuses selected-profile recommendations from the loaded payload.

### Executive PDF Report

Target state: generate a PDF for the selected snapshot, including region, period, alert level, map, indicators, trends, quality, recommendations, sources, methodology and limitations.

Current implementation shows the selected report filename as a CTA placeholder.

### Export Data

Target state: download CSV and JSON for the current view without secrets, tokens, local paths or unnecessary high-resolution geometries.

Current implementation shows the export filenames from the loaded payload.

### Footer

Must state that Mwangaza is a decision-support prototype and should be used with local knowledge. Institutional logos must only be used with permission; otherwise use text attribution.

## Implemented Now

- `/overview` route renders the main operational cockpit.
- `/` remains a compatibility route for the same screen.
- Sidebar uses page routes, not hash anchors.
- Risk map uses `ui_geometry` when present and explicit placeholder when missing.
- Active alerts, selected-region indicators, trends, recommendations and report/export references use existing `DashboardData`.
- Legacy hash URLs are cleaned on mount to prevent autoscroll.

## Future Sprint Notes

- Notification bell, user avatar and account menu are tracked by `sprint-57-overview-completion`.
- Real map home/zoom/layer controls and hover tooltips are tracked by `sprint-57-overview-completion`.
- Somali locale (`SO`) and segmented language buttons are tracked by `sprint-57-overview-completion`.
- Alert detail pages, filtered alert center links and alert priority tie-breakers beyond severity are tracked by `sprint-57-overview-completion`.
- Report generation and actual CSV/JSON download actions are tracked by `sprint-57-overview-completion`.
- Monthly indicator comparisons and baseline line-chart payloads are tracked by `sprint-57-overview-completion`.

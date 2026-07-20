# Region Interface Target

`/region` is the detailed country and pilot-area analysis screen for Mwangaza. It should connect observation, interpretation, alerting and early action without making the user infer meaning from raw satellite metrics alone.

## Visual Thesis

Operational drought cockpit: bright, restrained, map-led, and dense enough for repeated use by analysts without becoming decorative or marketing-like.

## Content Plan

1. Global shell: persistent brand, navigation, data status, notifications placeholder and account placeholder.
2. Region Explorer header: country, subregion, period and view controls.
3. Risk workspace: map or low-bandwidth table, selected-region summary and highlighted alert.
4. Evidence layer: indicator cards, score contribution bars, subnational ranking, trends and historical comparison.
5. Decision layer: recommended early actions, pilot-analysis explanation and responsible-use footer.

## Interaction Thesis

- Region selection updates every panel from the same already-loaded API/cache payload; it must not trigger direct Google Earth Engine calls from the browser.
- Low-bandwidth mode replaces heavy map/chart surfaces with compact tables while preserving alerts, indicators and recommendations.
- Hover/focus states expose context through tooltips and labels, not extra explanatory paragraphs.

## Required Sections

### Global Header

- Left: Mwangaza mark, product name and tagline.
- Center/right status strip:
  - Data source.
  - Last update.
  - Freshness badge: green current, yellow stale, red failed, gray demo/no data.
- Right placeholders:
  - Notifications icon.
  - User avatar.
  - Account dropdown affordance.

### Sidebar

Navigation items:

- Overview.
- Regions, active on `/region`.
- Alerts.
- Reports.
- About.

Controls:

- Language selector: `EN`, `SW`, `SO`.
- Low bandwidth mode toggle.

Language changes labels and recommendations when translations exist. It must not rewrite technical names, original data values or source identifiers.

### Region Explorer Controls

- Title: `Region Explorer`.
- Subtitle: `Country and subnational drought analysis`.
- Country selector updates the selected region from already-loaded dashboard/API data.
- Subregion selector supports:
  - `All districts`.
  - Pilot districts or pilot areas when data exists.
  - Disabled/placeholder state when subnational coverage is unavailable.
- Time-period selector shows only processed snapshots.
- View segmented control:
  - National view.
  - Pilot subnational view.

### Risk Map

Primary target: a district or pilot-area choropleth with visible legend.

Implementation choice: the React PWA uses `react-simple-maps` for SVG choropleths. This is intentional because it can render GeoJSON/TopoJSON shapes directly, does not require external map tiles, and fits low-bandwidth/offline constraints better than a tile-first map stack.

Severity colors:

- Green: Low.
- Yellow: Watch.
- Orange: Alert.
- Red: Severe.
- Gray: Not assessed.

Hover/focus details should include district/region name, alert level, score, NDVI anomaly, rainfall anomaly, data quality and snapshot date.

Current React implementation renders a real SVG map surface only when `ui_geometry` is present. If the public API does not expose geometries for the selected units, it shows an explicit `Map geometry pending` placeholder plus the regional readout table; it must not draw synthetic shapes as if they were geography.

### Region Summary

Shows:

- Region.
- Administrative level.
- Potentially exposed population.
- Last updated.
- Data quality.
- Current alert level.

Exposure must be labelled as potential exposure, not affected population.

### Highlighted Alert

Shows the strongest active alert for the selected region or a neutral placeholder when no active alert exists.

The `View all alerts` action should route to the alerts center with region and current-period filters once routing/filtering is implemented.

### Indicator Cards

Required cards:

- NDVI anomaly.
- Rainfall anomaly.
- Land Surface Temperature anomaly.
- Composite drought score.
- Potentially exposed population.

Each card should show current value, unit, source/detail and monthly comparison when available. If comparison is unavailable, show a compact `No comparison yet` placeholder.

### Why This Region Is At Risk

Explains the composite score with contribution bars:

- NDVI anomaly: 40%.
- Rainfall anomaly: 35%.
- Temperature anomaly: 25%.

When exact contribution payloads are unavailable, derive transparent provisional contributions from available current metrics and label the module as estimated from visible indicators.

### Subnational Ranking

Target state: sortable ranking by district/pilot unit with:

- Rank.
- District / Area.
- Alert level.
- Composite score.
- NDVI anomaly.
- Rainfall anomaly.
- Data quality.

Current placeholder is acceptable when the public API has only national or pilot-area rows. This limitation is already covered by Sprint 25 for pilot drilldown and Sprint 46 for a Northern Kenya end-to-end subnational scenario.

### Indicator Trends

Shows current period against historical baseline. Missing points must not be connected as if observed.

Current implementation can reuse available `RegionProfile.trends`; if live API has no trend payload for the selected region, show an explicit `Trend payload pending` placeholder.

### Historical Comparison

Compares current values against comparable historical drought episodes or historical periods. Periods must be seasonally comparable.

Current implementation can reuse `RegionProfile.historicalRows`; if absent, show a placeholder.

### Recommended Early Actions

Actions are decision support, not official orders. The detailed future version should include actor, priority, time horizon, evidence and target region.

Current implementation uses existing recommendation strings from the selected profile or active alert.

### About The Pilot Analysis

Explains:

- Enhanced detail exists only for configured pilots.
- The purpose is anticipatory local action.
- The rest of IGAD remains national-level in version 1.0 unless data coverage is explicitly available.

### Footer

Must state that Mwangaza is a decision-support prototype and estimates should be used alongside local knowledge. Institutional logos should only be used when permission is confirmed; otherwise use text attribution such as `Developed for the IGAD Hackathon 2026`.

## Implemented Now

- Northern Kenya demo selection covers Turkana, Marsabit and Isiolo offline; the active district drives its detail, report reference and simulated notification language.
- `/region` route renders a Region Explorer workspace in the React PWA.
- Country selection updates region summary, indicators, alert, recommendations, trends and history from the existing `DashboardData`.
- Low-bandwidth mode keeps a table-first shell.
- Missing subnational map/ranking/trend payloads are visible placeholders instead of silent demo claims.

## Future Sprint Notes

- Criterio obligatorio para `sprint-56-region-explorer-completion`: el mapa completo debe funcionar contra la API iniciada con `MWANGAZA_MODE=demo`, sin red, mostrando metadatos demo y conservando tabla/placeholder accesible cuando falte geometría.
- Full district-level Somalia map needs public API payloads with subnational geometries and metric rows. Related prior work: Sprint 25. Completion is now tracked by `sprint-56-region-explorer-completion`.
- Northern Kenya multi-district scenario is already planned in Sprint 46.
- Alerts center deep-link filters from `View all alerts` are tracked by `sprint-56-region-explorer-completion`.
- Real composite-score contribution payloads and month-over-month indicator deltas are tracked by `sprint-56-region-explorer-completion`.
- Account dropdown and notification inbox are visual placeholders until admin/security/notification flows are approved; their `/region` integration is tracked by `sprint-56-region-explorer-completion`.

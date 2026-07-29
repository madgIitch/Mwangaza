# Region Interface Target

`/region` is the detailed country and pilot-area analysis screen for Mwangaza. It should connect observation, interpretation, alerting and early action without making the user infer meaning from raw satellite metrics alone.

## Visual Thesis

Operational drought cockpit: bright, restrained, map-led, and dense enough for repeated use by analysts without becoming decorative or marketing-like.

## Content Plan

1. Global shell: persistent brand, navigation, data status, notifications placeholder and account placeholder.
2. Region Explorer header: country, subregion, period and view controls.
3. Risk workspace: a dominant administrative map paired with a contextual inspector for the active country or ADM1 unit.
4. Evidence layer: indicator cards, score contribution bars, a collapsible subnational ranking, trends and historical comparison.
5. Decision layer: the inspector's contextual early action, administrative-coverage explanation and responsible-use footer.

## Interaction Thesis

- The map, ADM1 selector and ranking share one active selection. Selecting an assessed boundary opens the same unit in the inspector and ranking; returning to the national view clears that selection.
- Region selection updates every panel from the same already-loaded API/cache payload; it must not trigger direct Google Earth Engine calls from the browser.
- The inspector prioritizes the selected score, severity, indicators, provenance and next action. Country-level coverage and period remain visible when an ADM1 is active.
- The ranking is collapsed by default and scrolls inside its own drawer, so its row count never determines the height of the primary map workspace.
- Low-bandwidth mode replaces SVG and chart surfaces with selectors, a compact selected-area table and a collapsible ranking while preserving alerts and evidence.
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
- About.
- Technical status.

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

The page uses locally cached, version-pinned geoBoundaries gbOpen ADM1 files as a neutral administrative reference layer for all eight IGAD countries. This reference layer is separate from the analytical region geometry used by GEE. A subdivision remains `Not assessed` unless the API provides a matching unit-level observation; a national score is never copied across all districts.

Implementation choice: the React PWA uses `react-simple-maps` for SVG choropleths. This is intentional because it can render GeoJSON/TopoJSON shapes directly, does not require external map tiles, and fits low-bandwidth/offline constraints better than a tile-first map stack.

Severity colors:

- Green: Low.
- Yellow: Watch.
- Orange: Alert.
- Red: Severe.
- Gray: Not assessed.

Hover/focus details should include district/region name, alert level, score, NDVI anomaly, rainfall anomaly, data quality and snapshot date.

The React implementation renders validated ADM1 boundaries from local assets and overlays only matching API observations. If a validated boundary asset is unavailable it shows an explicit unavailable state; it must not draw the coarse prototype bounding boxes as if they were geography. Polygon winding is normalized for the D3 projection before rendering so the country fits the viewport correctly.

The overlay join is exact on geoBoundaries `shapeISO` → API `boundary_iso`. Name matching is intentionally not used. Tooltips show the unit's own score, NDVI and rainfall values; any missing, non-conclusive or mismatched unit remains neutral gray.

Live coverage includes every ADM1 boundary of every enabled IGAD country by default. The backend computes the current period in a shared GEE batch, while country trends and historical comparisons remain aggregated to avoid multiplying remote work by district.

### Region Summary

Shows:

- Region.
- Administrative level.
- Potentially exposed population.
- Last updated.
- Data quality.
- Current alert level.

Exposure must be labelled as potential exposure, not affected population.

The desktop presentation is a dark contextual inspector beside the map rather than a passive summary card. When an ADM1 is selected it shows that unit's own values and provenance; national values are explicitly retained only as country context.

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

Explains the composite score with attributable points from the risk payload. Every indicator shows its normalized signal score, effective model weight, `weighted contribution = signal score × weight`, source and quality. The points add up to the explained composite score.

The normalized stacked bar is sized by actual weighted points, not by model weights alone. Its restrained blue-gray palette encodes composition only; risk severity remains exclusive to the map and status badges. Selecting an ADM1 uses that unit's own breakdown. When the exact national or ADM1 payload is absent, the module displays a pending state and never estimates or inherits another geography's contribution.

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

The implemented ranking is a collapsible, internally scrollable drawer below the primary workspace. Clicking a row updates the shared ADM1 selection and the map highlight without refetching data.

Severity and quality use the same badge vocabulary as the map inspector and tooltip. The first three positions receive stronger rank markers, while later row dividers are intentionally quieter.

### Indicator Trends

Shows current period against historical baseline. Missing points must not be connected as if observed.

Current implementation can reuse available `RegionProfile.trends`; if live API has no trend payload for the selected region, show an explicit `Trend payload pending` placeholder.

Current live trends remain country aggregates. While an ADM1 is selected, the heading names the country scope so the interface never presents national history as unit-level evidence.

Charts plot `value - baseline` around an explicit zero line. They expose the vertical scale, period labels and an accessible tooltip for value, baseline and difference; missing observations break the line.

Live mode materializes up to 24 monthly national points for every enabled country in one backend GEE batch. When no climatological baseline is present in the source payload, the chart uses and labels the mean of the available rolling series; this reference is not presented as an official climatology. Axis labels use compact month/year text while tooltips preserve the complete period.

### Historical Comparison

Compares current values against comparable historical drought episodes or historical periods. Periods must be seasonally comparable.

Current implementation can reuse `RegionProfile.historicalRows`; if absent, show a placeholder.

Rows are grouped by year and show compact signed deltas. Delta styling communicates direction only and does not imply that a positive or negative value is universally beneficial.

### Recommended Early Actions

Actions are decision support, not official orders. The detailed future version should include actor, priority, time horizon, evidence and target region.

Current implementation uses existing recommendation strings from the selected profile or active alert.

Region Explorer exposes only one primary action: the active regional alert with the highest severity, or the first regional recommendation when no alert exists. Additional recommendations remain outside this surface until the contract supplies explicit priority and time-horizon fields.

### About Administrative Coverage

Explains:

- Live detail covers every first-level administrative area in enabled IGAD countries.
- The purpose is anticipatory local action.
- Units remain explicitly unassessed whenever the source data is not conclusive.

### Footer

Must state that Mwangaza is a decision-support prototype and estimates should be used alongside local knowledge. Institutional logos should only be used when permission is confirmed; otherwise use text attribution such as `Developed for the IGAD Hackathon 2026`.

## Implemented Now

- Sprint 65 adds one compact `Drought continuation` block to the selected-ADM1 inspector.
  It compares `Experimental ML prediction` with `Historical reference` at 30 days and
  exposes only the historical reference at 60, 90 and 180 days.
- The block follows the exact ADM1 selection and never inherits a country or neighbouring
  unit probability. `not_applicable` and `unavailable` remain textual abstentions, never 0%.
- Validation, quality, Brier skill, IC95 and up to three non-causal associations remain
  visible without promoting the experimental estimate to operational guidance.
- Low-bandwidth mode preserves the same distinction in a text/table representation.
- Live/cache dashboard payloads accept only continuation snapshots with `is_demo=false`;
  demo dashboards accept only `is_demo=true`. A mismatch fails closed and never joins
  fixture geography to real probabilities. The inspector labels real results as
  `Materialized GEE-derived evidence`.
- Real-GEE smoke for Kenya returns 47 selectable Kenya ADM1 units and 121/121 conclusive
  IGAD ADM1 payloads, with `mode_live=true` and `not_demo=true`.

To run the real path locally, restart the API without `MWANGAZA_MODE=demo`:

```powershell
Remove-Item Env:MWANGAZA_MODE -ErrorAction SilentlyContinue
$env:MWANGAZA_API_DATA_MODE="live"
$env:MWANGAZA_DROUGHT_CONTINUATION_SNAPSHOT="data/models/drought-continuation-serving/snapshot.json"
uv run uvicorn mwangaza.api.app:app --reload
```

In a second terminal, start Vite in API mode (plain `npm run dev` intentionally
uses offline demo fixtures):

```powershell
npm run dev:api
```

The first connected response can be `data_mode=cache` while the background GEE
refresh is running. That cache contains observed materialized data, not demo
fixtures. Once the refresh completes, subsequent responses switch to
`data_mode=live` and identify `Google Earth Engine live query` as their source.
- The public API exposes complete region profiles and processed temporal cuts for both explicit demo and live/cache data.
- Region Explorer consumes explicit composite contributions, deterministic pilot rankings, live trends and seasonally comparable history.
- Country, pilot view and period controls operate on already-loaded payloads; `View all alerts` preserves region, period and active status.
- The map, ADM1 selector and ranking now drive one persistent selection and a contextual inspector with unit metrics, quality, period, provenance and early action.
- The ADM1 ranking is collapsed by default, scrolls independently and highlights the active unit without stretching the rest of the page.
- Low-bandwidth Region Explorer preserves country/ADM1 selection, selected-area evidence, ranking and filtered alerts without rendering the administrative SVG.
- Trends now use dated anomaly lines with a zero baseline and point tooltips; effective composite contributions use one neutral stacked bar with score accounting, source and quality.
- Live trends cover 24 monthly national aggregates by default, keep missing months as gaps and identify their effective baseline.
- Ranking rows share severity/quality badges with the map, emphasize the top three, and historical comparisons are grouped by year with compact deltas.
- The unpublished methodology is a quiet note rather than a link-like action; the inspector remains the only primary action surface.
- `smoke_tests/sprint56_region_explorer_real_gee.py` verifies the complete panel contract against real GEE without demo data.

- Northern Kenya demo selection covers Turkana, Marsabit and Isiolo offline; the active district drives its detail, report reference and simulated notification language.
- `/region` route renders a Region Explorer workspace in the React PWA.
- Country selection updates region summary, indicators, alert, recommendations, trends and history from the existing `DashboardData`.
- Low-bandwidth mode keeps a table-first shell.
- Missing subnational map/ranking/trend payloads are visible placeholders instead of silent demo claims.

## Future Sprint Notes

- Criterio obligatorio para `sprint-56-region-explorer-completion`: el mapa completo debe funcionar contra la API iniciada con `MWANGAZA_MODE=demo`, sin red, mostrando metadatos demo y conservando tabla/placeholder accesible cuando falte geometría.
- Full ADM1 maps for all eight IGAD countries are implemented through the Sprint 56 public API contract and locally versioned boundary assets.
- Northern Kenya multi-district scenario is already planned in Sprint 46.
- Alerts center deep-link filters from `View all alerts` are tracked by `sprint-56-region-explorer-completion`.
- Real composite-score contribution payloads and month-over-month indicator deltas are tracked by `sprint-56-region-explorer-completion`.
- Account dropdown and notification inbox are visual placeholders until admin/security/notification flows are approved; their `/region` integration is tracked by `sprint-56-region-explorer-completion`.
- Continuation materializes four horizons for all 121 ADM1 units, including 47/47 Kenya.
  The active state is homogeneous satellite evidence; NDMA is external validation and
  FEWS NET remains impact evidence. Inactive units show `not_applicable`, while active
  units always show at least the historical probability.
- The panel shows the analysis cut and every signal's observation date, age and quality.
  The top bar labels a connected request as `LIVE QUERY` while its date remains an
  observation window.
- Overview exposes the same `Persistent episodes` layer at IGAD country level. Countries
  with at least one active ADM1 episode use the same violet state, the tooltip reports
  active/evaluated counts, and a deep link opens Region Explorer with both country and
  episode layer preserved.
- The ADM1 map has two explicit layers. `Current risk` preserves the composite risk
  semaphore. `Persistent episodes` switches to a binary violet/neutral view, reports the
  active and evaluated counts for the selected country, and exposes duration plus 30-day
  ML/historical continuation on hover without losing the selected ADM1.

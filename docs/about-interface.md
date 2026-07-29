# About Interface Target

`/about` is an informational product screen, not an operational dashboard. It must help a new evaluator understand what Mwangaza does, how it works, which data sources it uses, what is implemented, and what its limits are.

## Visual Thesis

Quiet operational transparency: white working surfaces, green drought-action accents, compact explanatory blocks, and a simple Horn of Africa satellite-field illustration that supports the methodology story without implying live map coverage.

## Content Plan

1. About header: page title, methodology subtitle, snapshot/version chips, and a refresh placeholder for documentation/status only.
2. About Mwangaza: short explanation of the product plus conceptual illustration.
3. Capabilities: vegetation monitoring, rainfall monitoring, surface temperature, and early action.
4. Data Sources: transparent list of implemented or expected sources with platform/source distinction.
5. How Mwangaza Works: observe, compare, assess, act.
6. About This Project: IGAD Hackathon 2026 context, independent development, 29-day cycle, and purpose.
7. Pilot Coverage, Limitations, and System Status: responsible-use boundaries and current snapshot state.
8. Footer: copyright/open-source note and optional configured repository destination; legal/contact routes are not promoted in the product navigation.

## Interaction Thesis

- Capability and source rows should have clear hover/focus affordance but must not open fake detail pages.
- Methodology links point to existing docs when available; missing pages remain explicit placeholders.
- Theme switching is not implemented until a persisted theme contract exists.

## Sidebar Requirements

- Product identity remains `Mwangaza` with the tagline `Bringing Light to Early Action`.
- Navigation labels remain page routes: Overview, Regions, Active alerts, About and Technical status.
- About is highlighted when `/about` is active.
- The logo can later link to `/overview`; this is tracked as future shell polish.
- Decorative sidebar illustration and persisted Light/Dark theme switch are future scope.

## Top Header Requirements

- The global app topbar continues to show current source, mode, snapshot timestamp and API message.
- About itself has a local page header:
  - title `About`;
  - subtitle `Methodology, data sources and project information`;
  - version, environment/source mode and current data snapshot chips;
  - `Refresh status` placeholder that does not trigger Earth Engine processing.

## About Mwangaza

Primary text:

> Mwangaza is a satellite-powered drought early warning and early action platform designed for the IGAD region.

Supporting text:

> It combines vegetation, rainfall and land-surface-temperature indicators with historical baselines to help identify deteriorating conditions and translate them into actionable early-warning information.

Claims to avoid:

- Do not claim official disaster prediction.
- Do not claim to replace regional agencies or local validation.
- Do not equate exposure estimates with people affected.
- Do not present prototype alerts as authoritative declarations.

## Capabilities

- Vegetation Monitoring: NDVI and vegetation condition relative to seasonal baseline.
- Rainfall Monitoring: recent rainfall totals and deficit/anomaly signals.
- Surface Temperature: satellite-derived land surface temperature as complementary heat-stress evidence, not air temperature.
- Early Action: persistent episodes, recommendations and alerts derived from configured rules and observed indicators.

## Data Sources

The source list should distinguish processing platform from datasets:

- Google Earth Engine: cloud geospatial processing platform used to access and aggregate satellite and climate datasets.
- MODIS vegetation / NDVI: satellite imagery used to derive recent vegetation conditions.
- CHIRPS rainfall: satellite and station-based rainfall estimates used for recent totals and anomalies.
- MODIS Land Surface Temperature: satellite-derived land surface temperature signal.
- Administrative boundaries: national and pilot subnational aggregation geometry.
- Population or exposure source: show only as an estimate with source/year/resolution when available.

Future source-detail panels should include dataset, provider, unit, resolution, frequency, historical period, transformations, limitations and documentation link.

## How Mwangaza Works

1. Observe: retrieve NDVI, rainfall and land-surface temperature.
2. Compare: compare recent values with seasonal historical baselines.
3. Assess: derive anomalies, composite score, quality flags and drought level.
4. Act: surface persistent episodes, alerts, recommendations and portable data exports.

## Project Context

- Project: IGAD Hackathon 2026.
- Team: Independent developer.
- Development period: 29-day hackathon development cycle.
- Purpose: Transform satellite observations into understandable drought-risk signals and actionable early-action recommendations.

## Pilot Coverage

The interface must be explicit that current coverage is not full subnational operational coverage:

- National view for configured IGAD countries.
- Pilot subnational coverage where payloads exist.
- Somalia and northern Kenya can be shown as pilot examples when present in data.
- Expansion to additional subregions is future scope.

## Limitations

The page must visibly state:

- Mwangaza is a prototype.
- Alerts are not official public warnings.
- Satellite datasets may have delays, missing pixels or quality issues.
- Estimates require local validation.
- Composite scores depend on configurable thresholds.
- Exposure is `potentially_exposed`, not confirmed affected population.

## Implemented In Current Sprint

- `/about` route renders a dedicated About screen.
- Page explains product purpose, capabilities, data sources, methodology, project context, pilot coverage, limitations and system status.
- Current snapshot, source mode, forecast status and export labels reuse existing `DashboardData`.
- Missing theme switching, deep methodology pages, privacy policy, terms, contact page, source-detail drawers and refresh-status endpoint remain explicit placeholders.

## Sprint 60 Completion

- Light/Dark theme switching persists locally, defaults to the system preference and applies to the full shell. Low-bandwidth keeps content while omitting the decorative illustration and transitions.
- The logo links to `/overview`. Source rows expose accessible details for dataset/provider, unit, resolution, frequency, baseline, transformations, limitations and approved documentation links.
- `/methodology` (with `/about/provenance` preserved for compatibility), `/privacy`, `/terms` and `/contact` remain real public routes, but privacy, terms and contact are not linked from About.
- `GET /api/v1/about/status` exposes only versioned, public metadata and performs no Earth Engine work, pipeline refresh or write.
- MIT license metadata is visible. Repository and contact links render only when public destinations are configured; missing destinations remain explicit rather than invented.

## Pending / Future

- Institution-specific legal review and authenticated contact workflows remain outside the public prototype.
- Production deployments may configure public repository/contact URLs through deployment configuration.

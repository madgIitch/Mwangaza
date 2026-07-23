# Data Contracts

## About status

`GET /api/v1/about/status` is a cacheable, public, read-only metadata endpoint. It returns application and methodology versions, data mode, snapshot/documentation status, license and optional public repository/contact links. Its `refresh` object explicitly reports `kind=metadata_only`, `gee_triggered=false` and `writes_performed=false`. It never initializes Earth Engine, refreshes indicators or exposes private configuration.

Sprint 4 defines versioned data contracts in `mwangaza.contracts`.

## Version

All serialized payloads include:

- `schema_version`: `mwangaza.contracts.v1`
- `payload_type`: one of `indicator_observation`, `baseline`, `anomaly`,
  `risk_snapshot`, `alert`, or `forecast`

## Indicators

Valid indicators and units:

- `ndvi`: `index`
- `rainfall_mm`: `mm`
- `lst_c`: `celsius`
- `composite_score`: `score`
- `exposure`: `people_estimate`

`exposure` is an estimate and must not be presented as confirmed affected
people.

## Validation

Contracts reject:

- unknown `region_id`
- unknown indicators
- units incompatible with indicators
- non-finite numeric values
- inverted periods
- missing `schema_version`
- unknown `quality_flag`

`value=null` is allowed only when `quality_flag` is `no_data`,
`insufficient_history`, or `invalid`.

Fixtures and demo payloads must set `is_simulated=true`.
# Demo metadata

Fixture-derived payloads add `is_demo=true` plus `reference_date` or
`snapshot_id`. Existing `is_simulated` fields remain independent: they indicate
that an action or delivery was simulated, while `is_demo` identifies data origin.
# Region Explorer profiles (Sprint 56)

`GET /api/v1/snapshots/latest` includes additive `snapshot.region_profiles` and `snapshot.periods`. Profiles carry processed metrics, pilot-unit ranking, composite contributions, trends, seasonally comparable historical rows and recommendations. Each contribution contains `score`, effective `weight`, `weighted_contribution = score × weight`, `share_of_composite`, source and quality. The weighted contributions add up to the published composite score; they are score accounting, not severity categories. Period entries contain complete region/profile cuts already loaded by the backend; changing UI controls never calls Earth Engine directly. Production responses never fill missing live/cache modules with demo fixtures.

Live profile trends contain 24 national monthly aggregates by default (`MWANGAZA_LIVE_TREND_MONTHS`, clamped to 12-24). All enabled countries and monthly windows are first materialized in one GEE graph/request. If that regional graph fails, the backend retries the same 12-24 monthly windows once per enabled country and isolates individual failures; it never silently reduces trend coverage to the initially selected country. These trend-only observations are marked with `metadata.trend_series=true` and never become period-selector entries or historical-comparison candidates. `baseline_label` identifies whether points use a source baseline or the mean of available monthly values in the rolling series. Missing monthly values remain explicit gaps.

Each profile can additionally publish `administrative_units`. Every row contains stable `region_id`, geoBoundaries `boundary_id` and `boundary_iso`, name, parent, ADM level, period, composite score, risk level, quality, `source_mode`, geometry provenance, rank, numeric `ndvi`, `rainfall_mm` and `lst_c` metrics, plus its own additive `contributions` array. A client must not reuse the national contribution breakdown for a selected ADM1; an absent array means the unit breakdown is pending. The field is additive and may be empty when ADM1 processing is disabled or unavailable.

Live GEE computes ADM1 only for the current period. By default it processes every ADM1 unit in every `MWANGAZA_ENABLED_COUNTRIES` country (all eight IGAD countries by default) in one batched `reduceRegions` request. `MWANGAZA_GEE_ADM1_COUNTRIES` explicitly restricts that batch and `MWANGAZA_GEE_ADM1_ENABLED=false` disables it. A failed unit is isolated from other units and omitted from the contract, so clients render it as not assessed rather than inheriting national risk.

Live API reads use stale-while-revalidate semantics. A valid materialized response is returned immediately while one process-local background refresh updates GEE data; `/alerts` and `/forecasts` never wait behind that remote calculation. The PWA polls the snapshot while `data_mode=cache` and promotes it to `live` without a page reload. Successful live loads atomically persist a last-known-good payload batch, and an incomplete newer cache period cannot displace an older usable score for the preferred region.

The ADM1 NDVI batch accepts MOD13Q1 `SummaryQA` values 0 (good) and 1 (marginal but useful), records the accepted values in indicator metadata and rejects snow/ice and cloudy values 2-3. This ADM1-specific rule prevents small administrative areas from becoming falsely unassessed while retaining real source pixels; aggregated country/history queries keep the stricter configured QA filter.

# Alerts Center contract (Sprint 58)

`GET /api/v1/alerts` accepts `q`, `region`, `severity`, `status`, `period`, `limit` and `offset`. Valid lifecycle statuses are `preventive`, `active`, `monitoring`, `resolved` and `superseded`; invalid severity or status values return a structured `400 invalid_request`. The response includes a filtered `summary` alongside paginated items.

Every alert publishes a stable `id`, region, severity, status, alert type, period boundaries, issued/updated/resolved timestamps, score, quality, evidence, recommended action, recommendation metadata, lifecycle events and simulated notification entries. Persisted IDs are repository-backed; fixture IDs are deterministic. Missing history is represented conservatively and never changes alert state.

Simulated notification rows include channel, masked recipient, content, status, timestamp and `is_simulated=true`. These rows are previews only: the public API has no send endpoint and does not contact SMS, email or messaging providers.

Filtered downloads reuse the same query contract:

- `GET /api/v1/exports/alerts?format=csv|json`
- `GET /api/v1/reports/alerts`

The Alerts Center consumes only API/cache payloads, including in low-bandwidth mode. Browser interaction never queries Earth Engine directly.
## Reports Center API

- `GET /api/v1/reports` lists stable report records with filters and pagination.
- `POST /api/v1/reports?region_id=<id>` validates the materialized regional record and logs generation; optional `period`, `template_id` and `language` query parameters are validated.
- `GET /api/v1/reports/<id>` returns record, audit events and an explicitly labelled HTML preview.
- `GET /api/v1/reports/<id>/download?format=pdf|csv|json` returns a non-empty attachment for ready reports.
- Scheduling, template mutation, sharing and distribution have no public mutation contract and remain `pending_contract`.

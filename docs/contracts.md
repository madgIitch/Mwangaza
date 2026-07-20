# Data Contracts

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

`GET /api/v1/snapshots/latest` includes additive `snapshot.region_profiles` and `snapshot.periods`. Profiles carry processed metrics, pilot-unit ranking, composite contributions, trends, seasonally comparable historical rows and recommendations. Period entries contain complete region/profile cuts already loaded by the backend; changing UI controls never calls Earth Engine directly. Production responses never fill missing live/cache modules with demo fixtures.

Each profile can additionally publish `administrative_units`. Every row contains stable `region_id`, geoBoundaries `boundary_id` and `boundary_iso`, name, parent, ADM level, period, composite score, risk level, quality, `source_mode`, geometry provenance, rank and numeric `ndvi`, `rainfall_mm` and `lst_c` metrics. The field is additive and may be empty when ADM1 processing is disabled or unavailable.

Live GEE computes ADM1 only for the current period. The default bounded scope is all Somalia ADM1 units plus Turkana, Marsabit and Isiolo in Kenya; `MWANGAZA_GEE_ADM1_COUNTRIES` opts complete countries into processing and `MWANGAZA_GEE_ADM1_ENABLED=false` disables it. A failed unit is isolated from other units and omitted from the contract, so clients render it as not assessed rather than inheriting national risk.

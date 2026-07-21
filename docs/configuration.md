# Configuration

Sprint 1 centralizes runtime settings in `mwangaza.config`.

When `load_settings()` is called without an explicit environment mapping, Mwangaza
loads `MWANGAZA_*` values from a `.env` file in the current working directory and
then overlays the real process environment. This lets local commands work from
the repo root while keeping deployment behavior compatible with managed
environment variables and secret managers.

## Profiles

- `local`: default developer profile; no external credentials required.
- `test`: test profile; must run without real credentials.
- `demo`: local fixture profile; uses `MWANGAZA_DEMO_FIXTURE_DIR` and does not call remote services.
- `production`: requires `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT` and `MWANGAZA_GEE_PRIVATE_KEY_JSON`.

## Public Variables

- `MWANGAZA_ENV`
- `MWANGAZA_LOG_LEVEL`
- `MWANGAZA_DATA_DIR`
- `MWANGAZA_CACHE_DIR`
- `MWANGAZA_DEMO_FIXTURE_DIR`
- `MWANGAZA_ENABLED_COUNTRIES`
- `MWANGAZA_CLIMATOLOGY_START_YEAR`
- `MWANGAZA_CLIMATOLOGY_END_YEAR`
- `MWANGAZA_CLIMATOLOGY_MIN_YEARS`
- `MWANGAZA_MAX_REMOTE_PIXELS`
- `MWANGAZA_GEE_PROJECT`
- `MWANGAZA_NDVI_COLLECTION`
- `MWANGAZA_RAINFALL_COLLECTION`
- `MWANGAZA_LIVE_TREND_MONTHS` (12-24, default `24`; national monthly aggregates only)
- `MWANGAZA_GEE_ADM1_ENABLED`
- `MWANGAZA_GEE_ADM1_COUNTRIES`

`MWANGAZA_ENABLED_COUNTRIES` is a comma-separated list of IGAD ISO3 codes:
`KEN,ETH,SOM,SDN,SSD,UGA,DJI,ERI`.

`MWANGAZA_LIVE_TREND_MONTHS` controls the rolling national trend horizon. The deprecated `MWANGAZA_LIVE_TREND_POINTS` remains a compatibility alias, but values are clamped to 12-24 months. Trend collection is batched and does not extend the historical query to every ADM1 unit.

## Private Variables

- `MWANGAZA_GEE_SERVICE_ACCOUNT`
- `MWANGAZA_GEE_PRIVATE_KEY_JSON`

Private values must not appear in `repr(settings)`, logs, HTTP responses or dashboard errors.
# Explicit offline demo mode

`MWANGAZA_MODE=demo` is the sole explicit switch for the offline demo baseline.
It requires no Earth Engine credentials and does not initialize remote services.
Production may use an explicitly identified valid cache, but never falls back to
demo implicitly. Restore managed demo state with `python scripts/reset_demo.py`.

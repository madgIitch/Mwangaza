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
- `MWANGAZA_MAX_REMOTE_PIXELS`
- `MWANGAZA_GEE_PROJECT`

`MWANGAZA_ENABLED_COUNTRIES` is a comma-separated list of IGAD ISO3 codes:
`KEN,ETH,SOM,SDN,SSD,UGA,DJI,ERI`.

## Private Variables

- `MWANGAZA_GEE_SERVICE_ACCOUNT`
- `MWANGAZA_GEE_PRIVATE_KEY_JSON`

Private values must not appear in `repr(settings)`, logs, HTTP responses or dashboard errors.

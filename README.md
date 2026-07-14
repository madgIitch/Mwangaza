# Mwangaza

Bringing Light to Early Action.

Mwangaza is a satellite-powered drought early warning and early action platform for the IGAD region. Sprint 0 is a foundation stub: it provides importable modules, stable public commands, and safe placeholder entrypoints without calling Google Earth Engine or any remote data service.

## Requirements

- Python 3.11+
- `make` on CI/Linux-like environments

On Windows, run the Python commands shown in the Makefile targets if `make` is unavailable.

## Install

```bash
python -m pip install -e .
python -c "import mwangaza; print(mwangaza.__version__)"
```

The version command prints `0.0.1`.

## Quality Gates

The local commands are the same commands used by CI. On Windows, the Makefile resolves the Python managed install under `%LOCALAPPDATA%`; on Linux CI, it runs with `PYTHON=python`. The targets set `PYTHONPATH=src` so they do not depend on a prior global install:

```bash
make lint
make typecheck
make test
```

Sprint 0 configures Ruff, MyPy and Pytest in `pyproject.toml` for later development. The current gates use standard-library checks so the foundation can be installed and verified without downloading development tools.

## Entrypoints

Dashboard:

```bash
streamlit run app.py
```

The dashboard shows the Mwangaza name, tagline, basic technical status, and a visible `foundation stub` notice. It does not show real drought data or simulated production data.

API:

```bash
uvicorn mwangaza.api.app:app --reload
```

The ASGI app exposes `GET /health` and returns a stub health payload. It does not require credentials.

Refresh dry-run:

```bash
python -m mwangaza.data.refresh --dry-run
```

The dry run prints a foundation message and does not query remote services.

## Secrets

Copy `.env.example` only as a local starting point. Its values are placeholders and must not be treated as real Earth Engine credentials.

Public configuration:

- `MWANGAZA_ENV`: `local`, `test`, `demo`, or `production`; defaults to `local`.
- `MWANGAZA_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `MWANGAZA_DATA_DIR`, `MWANGAZA_CACHE_DIR`, `MWANGAZA_DEMO_FIXTURE_DIR`: local paths.
- `MWANGAZA_ENABLED_COUNTRIES`: comma-separated IGAD ISO3 list from `KEN,ETH,SOM,SDN,SSD,UGA,DJI,ERI`.
- `MWANGAZA_CLIMATOLOGY_START_YEAR` and `MWANGAZA_CLIMATOLOGY_END_YEAR`: four-digit year range.
- `MWANGAZA_MAX_REMOTE_PIXELS`: positive integer guardrail.
- `MWANGAZA_GEE_PROJECT`: non-secret project identifier, required only in production.

Private configuration:

- `MWANGAZA_GEE_SERVICE_ACCOUNT`: secret service account value, required only in production.
- `MWANGAZA_GEE_PRIVATE_KEY_JSON`: secret JSON object, required only in production.

`Settings` redacts private values from `repr`, API health output and user-facing error messages. The `test` and `demo` profiles do not require real credentials.

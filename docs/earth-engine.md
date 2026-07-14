# Google Earth Engine Access Check

Sprint 2 adds a mockable Earth Engine authentication adapter. Automated tests do not call Earth Engine.

## Required Variables

Set these only in a private shell or secret manager:

- `MWANGAZA_ENV=production`
- `MWANGAZA_GEE_PROJECT`
- `MWANGAZA_GEE_SERVICE_ACCOUNT`
- `MWANGAZA_GEE_PRIVATE_KEY_JSON`

`MWANGAZA_GEE_PRIVATE_KEY_JSON` must be the service account JSON object as an environment variable. Do not write it to disk and do not commit it.

For local development, these variables can live in a private `.env` file in the
repo root. Mwangaza reads that file automatically when commands are run from the
repo root. Variables already exported in the shell override `.env`.

## Manual Check

Run:

```bash
python -m mwangaza.gee.auth --check
```

Expected success:

```json
{"gee": {"status": "ok", "configured": true}}
```

Any other status is stable and actionable: `auth_error`, `permission_error`, `quota_error`, or `network_error`. The output is sanitized and must not include service account values, private keys, client email values, or the raw JSON secret.

# Smoke Tests

Manual smoke tests for production-like integrations live here.

Rules:

- Use these for human validation before closing `review_pending` sprints that touch real external data.
- Keep automated unit tests deterministic with fakes/mocks; do not make CI depend on credentials, network, quota, or Earth Engine availability.
- Read credentials and local secret paths from environment variables.
- Never print private keys, service accounts, client emails, or local secret paths.
- Validate sanitized payloads before printing results.

## Earth Engine

For GEE-backed smoke tests, set:

```powershell
$env:MWANGAZA_GEE_SERVICE_ACCOUNT_JSON_PATH = "C:\path\to\service-account.json"
```

Then run the target script from the repository root, for example:

```powershell
py smoke_tests\sprint12_temperature_anomaly_real_gee.py
```

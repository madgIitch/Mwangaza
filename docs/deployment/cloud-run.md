# Container deployment

Mwangaza is packaged as three non-root image targets:

- `api`: Python ASGI API on port `8080`;
- `web`: compiled React SPA served by unprivileged Nginx on port `8080`.
- `refresh`: the API Python runtime with the scheduled refresh CLI as its entrypoint.

The web service proxies `/api/**`, `/health` and `/ready` to the API. The browser therefore
uses one public origin and does not need CORS configuration or an embedded API URL.

## Local demo smoke test

Docker Desktop or another compatible Docker daemon must be running.

```powershell
uv run python scripts/smoke_containers.py
```

The command builds both targets, starts Compose, waits for API health/readiness, checks a
deep SPA route and verifies the same-origin snapshot. It then stops only this Compose stack.
To inspect it interactively:

```powershell
uv run python scripts/smoke_containers.py --keep
```

Open `http://127.0.0.1:18080`. The API remains directly visible at
`http://127.0.0.1:18081/health`. These isolated ports deliberately avoid the normal Vite and
API development ports. Stop it afterwards with:

```powershell
docker compose down --remove-orphans
```

The Compose profile is explicitly demo-only and neither reads nor initializes GEE
credentials.

## Image construction

```powershell
docker build --target api -t mwangaza-api:local .
docker build --target web -t mwangaza-web:local .
docker build --target refresh -t mwangaza-refresh:local .
```

The final API image contains the installed Python package and versioned demo fixtures. The
web image contains only the compiled frontend, Nginx configuration and static assets.
`.dockerignore` excludes local histories, models, caches, virtual environments, submissions,
Git metadata and secret-shaped files.

## Public Cloud Run demo

Prerequisites:

1. Google Cloud CLI installed and authenticated with `gcloud auth login`.
2. A project with billing enabled.
3. Permission to enable APIs, build images, write Artifact Registry and deploy Cloud Run.

Run from the repository root:

```powershell
.\scripts\deploy_cloud_run.ps1 `
  -ProjectId YOUR_PROJECT_ID `
  -Region europe-west1 `
  -Tag sprint53
```

The script performs six explicit stages:

1. selects the project and enables Cloud Run, Artifact Registry and Cloud Build;
2. creates the Docker repository if absent;
3. builds and pushes both image targets through Cloud Build;
4. deploys the public demo API with startup and liveness probes;
5. deploys the public web service with the API URL injected at runtime;
6. verifies `/healthz`, proxied `/health` and `/api/v1/snapshots/latest`.

The final line prints the HTTPS URL to use as the first Devpost “Try it out” link. Both
services use `--allow-unauthenticated` because the submitted prototype must be accessible to
judges without a Google account.

## Production configuration and secrets

The public deployment script intentionally starts in `MWANGAZA_MODE=demo`. Live production
data is enabled only after the scheduled Job has successfully published its first snapshot.

Never pass private values through `Dockerfile`, build arguments, Cloud Build substitutions or
committed environment files. Store them in Secret Manager and pin a version when exposing a
secret as an environment variable. For example:

```powershell
gcloud secrets create mwangaza-gee-private-key-json --replication-policy=automatic
gcloud secrets versions add mwangaza-gee-private-key-json --data-file=PRIVATE_KEY.json
```

`MWANGAZA_GEE_SERVICE_ACCOUNT` and `MWANGAZA_GEE_PROJECT` remain non-secret runtime values.
A production service does not silently revert to demo if credentials or materialized data
are missing.

## Scheduled production refresh

Prerequisites beyond the public demo deployment:

1. an Earth Engine service account authorized for the configured project;
2. its private-key JSON stored in Secret Manager;
3. a globally unique Cloud Storage bucket name;
4. permission to create service accounts, a Cloud Run Job, Scheduler trigger, log metric and
   Monitoring policy.

Deploy the refresh plane with:

```powershell
.\scripts\deploy_scheduled_refresh.ps1 `
  -ProjectId YOUR_PROJECT_ID `
  -BucketName YOUR_UNIQUE_BUCKET `
  -GeeProject YOUR_GEE_PROJECT `
  -GeeServiceAccount gee-reader@YOUR_PROJECT_ID.iam.gserviceaccount.com `
  -GeePrivateKeySecret mwangaza-gee-private-key-json `
  -Tag git-SHORT_SHA
```

The script builds the same locked `refresh` image, creates separate refresh and scheduler
identities, grants object-write, secret-read and Job-invoke permissions, deploys one Job task,
executes it once, and only then switches the API to production cache mode. Cloud Scheduler
invokes the Cloud Run Jobs API daily at `03:00 UTC` by default. Change this with `-Schedule`
and `-TimeZone`.

If the requested tag is already present in Artifact Registry, pass `-SkipBuild` to verify and
reuse that immutable image instead of starting another Cloud Build.

The Job calls exactly:

```text
python -m mwangaza.data.refresh
```

The CLI performs the GEE query. HTTP requests never run GEE: the API reads
  `live-dashboard-last-good.json` from a dedicated read-only Cloud Storage mount at
  `/mnt/mwangaza-refresh`. `MWANGAZA_REFRESH_CACHE_DIR` keeps that mount separate from the
  API's writable application cache and SQLite state. The Job itself uses the
Cloud Storage API because FUSE does not provide the generation preconditions required for a
safe distributed lock.

For every run, the bucket retains:

- `mwangaza-refresh/snapshots/PERIOD/RUN_ID.json`: immutable rollback snapshot;
- `mwangaza-refresh/live-dashboard-last-good.json`: atomically replaced stable snapshot;
- `mwangaza-refresh/refresh-status.json`: last attempt, last success, observation age and
  quality summary;
- `mwangaza-refresh/locks/active.json`: temporary generation-guarded lock carrying its period.

A failed query or validation exits non-zero, records a sanitized failure and does not replace
the stable snapshot. The deployment creates the `mwangaza_refresh_failures` log metric and a
Monitoring incident policy. Supply `-NotificationChannel` to attach an existing channel.

Local contract checks never contact GEE or write data:

```powershell
uv run python -m mwangaza.data.refresh --dry-run --period 2026-07-30
```

## Health and diagnosis

- API `/health`: liveness and sanitized configuration state.
- API `/ready`: readiness; returns non-200 when required runtime resources are unavailable.
- Web `/healthz`: Nginx process and static-serving liveness.
- Web `/health` and `/ready`: proxied API state.

Useful commands:

```powershell
gcloud run services describe mwangaza-web --region europe-west1
gcloud run services describe mwangaza-api --region europe-west1
gcloud run services logs read mwangaza-api --region europe-west1 --limit 100
gcloud run jobs executions list --job mwangaza-refresh --region europe-west1
gcloud run jobs logs read mwangaza-refresh --region europe-west1 --limit 100
gcloud scheduler jobs describe mwangaza-refresh-daily --location europe-west1
```

Do not paste raw environment values or unredacted GEE errors into public issues or the demo
video.

## Update and rollback

Use a unique immutable tag for each submission or commit instead of overwriting the previous
image tag:

```powershell
.\scripts\deploy_cloud_run.ps1 -ProjectId YOUR_PROJECT_ID -Tag git-SHORT_SHA
```

Cloud Run creates an immutable revision for each deployment. List revisions and send all
traffic back to a known-good one with:

```powershell
gcloud run revisions list --service mwangaza-web --region europe-west1
gcloud run services update-traffic mwangaza-web `
  --region europe-west1 `
  --to-revisions PREVIOUS_WEB_REVISION=100
```

Repeat the traffic command for `mwangaza-api` if the API revision also changed. Validate the
web `/healthz`, proxied `/health` and the persistent-episode route after every rollout or
rollback.

Snapshot rollback is independent of a container rollback. Select an immutable object only
after inspecting its embedded `refresh.run_id`, `effective_observation_at` and quality summary,
then replace the stable object:

```powershell
gcloud storage cp `
  gs://YOUR_BUCKET/mwangaza-refresh/snapshots/PERIOD/RUN_ID.json `
  gs://YOUR_BUCKET/mwangaza-refresh/live-dashboard-last-good.json
```

Keep the corresponding immutable object. Do not delete later snapshots during rollback; they
are the audit trail. Run the Job again after resolving the upstream issue so that
`refresh-status.json` and the stable snapshot return to the same successful run.

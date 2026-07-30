# Container deployment

Sprint 53 packages Mwangaza as two independently deployable, non-root images:

- `api`: Python ASGI API on port `8080`;
- `web`: compiled React SPA served by unprivileged Nginx on port `8080`.

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

The deployment script intentionally deploys `MWANGAZA_MODE=demo`. It does not claim to
publish live GEE data. A production revision must explicitly set production mode, configure
the materialized continuation snapshot and provide its GEE identity.

Never pass private values through `Dockerfile`, build arguments, Cloud Build substitutions or
committed environment files. Store them in Secret Manager and pin a version when exposing a
secret as an environment variable. For example:

```powershell
gcloud run services update mwangaza-api `
  --region europe-west1 `
  --update-env-vars MWANGAZA_MODE=production,MWANGAZA_API_DATA_MODE=live,MWANGAZA_GEE_PROJECT=YOUR_GEE_PROJECT `
  --update-secrets MWANGAZA_GEE_PRIVATE_KEY_JSON=mwangaza-gee-private-key:1
```

Also configure `MWANGAZA_GEE_SERVICE_ACCOUNT` as a non-secret runtime value or use the Cloud
Run service identity where the application contract permits it. A production service must
not silently revert to demo if credentials or materialized data are missing.

The scheduled refresh and durable publication of real production snapshots belong to the
next deployment stage; they are not fabricated or baked into these images.

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

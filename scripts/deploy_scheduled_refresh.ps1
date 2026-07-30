[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$BucketName,
    [Parameter(Mandatory = $true)][string]$GeeProject,
    [Parameter(Mandatory = $true)][string]$GeeServiceAccount,
    [Parameter(Mandatory = $true)][string]$GeePrivateKeySecret,
    [string]$Region = "europe-west1",
    [string]$Repository = "mwangaza",
    [string]$ServicePrefix = "mwangaza",
    [string]$Tag = "manual",
    [string]$Schedule = "0 3 * * *",
    [string]$TimeZone = "Etc/UTC",
    [string]$NotificationChannel = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$CommandArgs)
    & gcloud @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud failed: $($CommandArgs -join ' ')"
    }
}

function Test-Gcloud {
    param([Parameter(Mandatory = $true)][string[]]$CommandArgs)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        & gcloud @CommandArgs *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Ensure-ServiceAccount {
    param([Parameter(Mandatory = $true)][string]$Name, [Parameter(Mandatory = $true)][string]$DisplayName)
    if (-not (Test-Gcloud @("iam", "service-accounts", "describe", "$Name@$ProjectId.iam.gserviceaccount.com"))) {
        Invoke-Gcloud @("iam", "service-accounts", "create", $Name, "--display-name=$DisplayName")
    }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud CLI is required. Install it and run 'gcloud auth login' first."
}

$refreshJob = "$ServicePrefix-refresh"
$schedulerJob = "$ServicePrefix-refresh-daily"
$apiService = "$ServicePrefix-api"
$refreshIdentityName = "$ServicePrefix-refresh"
$schedulerIdentityName = "$ServicePrefix-scheduler"
$refreshIdentity = "$refreshIdentityName@$ProjectId.iam.gserviceaccount.com"
$schedulerIdentity = "$schedulerIdentityName@$ProjectId.iam.gserviceaccount.com"
$registry = "$Region-docker.pkg.dev/$ProjectId/$Repository"
$refreshImage = "$registry/mwangaza-refresh:$Tag"

Write-Host "[1/9] Selecting project and enabling scheduler services"
Invoke-Gcloud @("config", "set", "project", $ProjectId)
Invoke-Gcloud @(
    "services", "enable", "run.googleapis.com", "cloudscheduler.googleapis.com",
    "storage.googleapis.com", "secretmanager.googleapis.com", "logging.googleapis.com",
    "monitoring.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com"
)

Write-Host "[2/9] Checking the runtime secret and storage bucket"
Invoke-Gcloud @("secrets", "describe", $GeePrivateKeySecret)
if (-not (Test-Gcloud @("storage", "buckets", "describe", "gs://$BucketName"))) {
    Invoke-Gcloud @("storage", "buckets", "create", "gs://$BucketName", "--location=$Region", "--uniform-bucket-level-access")
}

Write-Host "[3/9] Creating least-privilege service identities"
Ensure-ServiceAccount -Name $refreshIdentityName -DisplayName "Mwangaza scheduled refresh"
Ensure-ServiceAccount -Name $schedulerIdentityName -DisplayName "Mwangaza scheduler invoker"
Invoke-Gcloud @("storage", "buckets", "add-iam-policy-binding", "gs://$BucketName", "--member=serviceAccount:$refreshIdentity", "--role=roles/storage.objectUser")
Invoke-Gcloud @("secrets", "add-iam-policy-binding", $GeePrivateKeySecret, "--member=serviceAccount:$refreshIdentity", "--role=roles/secretmanager.secretAccessor")
Invoke-Gcloud @("projects", "add-iam-policy-binding", $ProjectId, "--member=serviceAccount:$schedulerIdentity", "--role=roles/run.invoker")

Write-Host "[4/9] Building the locked refresh image"
if ($SkipBuild) {
    Invoke-Gcloud @("artifacts", "docker", "images", "describe", "$refreshImage")
    Write-Host "Using existing image: $refreshImage"
} else {
    Invoke-Gcloud @(
        "builds", "submit", ".", "--config=infrastructure/cloudbuild.yaml",
        "--ignore-file=.dockerignore",
        "--substitutions=_REGION=$Region,_REPOSITORY=$Repository,_TAG=$Tag"
    )
}

Write-Host "[5/9] Deploying the single-task Cloud Run Job"
Invoke-Gcloud @(
    "run", "jobs", "deploy", $refreshJob, "--region=$Region", "--image=$refreshImage",
    "--service-account=$refreshIdentity", "--tasks=1", "--parallelism=1",
    "--max-retries=1", "--task-timeout=3600s", "--cpu=2", "--memory=4Gi",
    "--set-env-vars=MWANGAZA_ENV=production,MWANGAZA_MODE=production,MWANGAZA_REFRESH_BUCKET=$BucketName,MWANGAZA_GEE_PROJECT=$GeeProject,MWANGAZA_GEE_SERVICE_ACCOUNT=$GeeServiceAccount",
    "--set-secrets=MWANGAZA_GEE_PRIVATE_KEY_JSON=$GeePrivateKeySecret`:latest"
)

Write-Host "[6/9] Executing the first refresh before switching the API"
Invoke-Gcloud @("run", "jobs", "execute", $refreshJob, "--region=$Region", "--wait")

Write-Host "[7/9] Mounting the published snapshot read-only in the API"
$apiIdentity = (& gcloud run services describe $apiService --region $Region --format="value(spec.template.spec.serviceAccountName)").Trim()
if (-not $apiIdentity) {
    $projectNumber = (& gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()
    $apiIdentity = "$projectNumber-compute@developer.gserviceaccount.com"
}
Invoke-Gcloud @("storage", "buckets", "add-iam-policy-binding", "gs://$BucketName", "--member=serviceAccount:$apiIdentity", "--role=roles/storage.objectViewer")
Invoke-Gcloud @(
    "run", "services", "update", $apiService, "--region=$Region", "--execution-environment=gen2",
    "--add-volume=name=mwangaza-refresh,type=cloud-storage,bucket=$BucketName,readonly=true,mount-options=only-dir=mwangaza-refresh;uid=10001;gid=10001",
    "--add-volume-mount=volume=mwangaza-refresh,mount-path=/mnt/mwangaza-refresh",
    "--update-env-vars=MWANGAZA_ENV=production,MWANGAZA_MODE=production,MWANGAZA_API_DATA_MODE=cache,MWANGAZA_REFRESH_CACHE_DIR=/mnt/mwangaza-refresh"
)

Write-Host "[8/9] Creating or updating the daily Cloud Scheduler trigger"
$runUri = "https://run.googleapis.com/v2/projects/$ProjectId/locations/$Region/jobs/$refreshJob`:run"
$schedulerExists = Test-Gcloud @("scheduler", "jobs", "describe", $schedulerJob, "--location=$Region")
$schedulerVerb = if ($schedulerExists) { "update" } else { "create" }
Invoke-Gcloud @(
    "scheduler", "jobs", $schedulerVerb, "http", $schedulerJob, "--location=$Region",
    "--schedule=$Schedule", "--time-zone=$TimeZone", "--uri=$runUri", "--http-method=POST",
    "--oauth-service-account-email=$schedulerIdentity", "--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform",
    "--message-body={}", "--max-retry-attempts=1", "--attempt-deadline=180s"
)

Write-Host "[9/9] Installing failure metric and alert policy"
$logFilter = "resource.type=`"cloud_run_job`" AND resource.labels.job_name=`"$refreshJob`" AND jsonPayload.component=`"scheduled_refresh`" AND jsonPayload.severity=`"ERROR`""
if (Test-Gcloud @("logging", "metrics", "describe", "mwangaza_refresh_failures")) {
    Invoke-Gcloud @("logging", "metrics", "update", "mwangaza_refresh_failures", "--description=Failed scheduled Mwangaza refresh runs", "--log-filter=$logFilter")
} else {
    Invoke-Gcloud @("logging", "metrics", "create", "mwangaza_refresh_failures", "--description=Failed scheduled Mwangaza refresh runs", "--log-filter=$logFilter")
}
$existingPolicy = [string](& gcloud monitoring policies list --filter="displayName='Mwangaza scheduled refresh failures'" --format="value(name)" --limit=1)
$existingPolicy = $existingPolicy.Trim()
if (-not $existingPolicy) {
    $policyArgs = @("monitoring", "policies", "create", "--policy-from-file=infrastructure/scheduler/refresh-failure-policy.json")
    if ($NotificationChannel) { $policyArgs += "--notification-channels=$NotificationChannel" }
    Invoke-Gcloud $policyArgs
}

Write-Host "Scheduled refresh ready: $refreshJob via $schedulerJob ($Schedule $TimeZone)"
Write-Host "Stable snapshot: gs://$BucketName/mwangaza-refresh/live-dashboard-last-good.json"

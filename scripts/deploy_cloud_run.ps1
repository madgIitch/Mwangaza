[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [string]$Region = "europe-west1",
    [string]$Repository = "mwangaza",
    [string]$ServicePrefix = "mwangaza",
    [string]$Tag = "manual"
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

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud CLI is required. Install it and run 'gcloud auth login' first."
}

$apiService = "$ServicePrefix-api"
$webService = "$ServicePrefix-web"
$registry = "$Region-docker.pkg.dev/$ProjectId/$Repository"
$apiImage = "$registry/mwangaza-api:$Tag"
$webImage = "$registry/mwangaza-web:$Tag"

Write-Host "[1/6] Selecting project and enabling required services"
Invoke-Gcloud @("config", "set", "project", $ProjectId)
Invoke-Gcloud @("services", "enable", "run.googleapis.com", "artifactregistry.googleapis.com", "cloudbuild.googleapis.com")

Write-Host "[2/6] Ensuring Artifact Registry repository exists"
if (-not (Test-Gcloud @("artifacts", "repositories", "describe", $Repository, "--location=$Region"))) {
    Invoke-Gcloud @("artifacts", "repositories", "create", $Repository, "--repository-format=docker", "--location=$Region", "--description=Mwangaza container images")
}

Write-Host "[3/6] Building and pushing API and web images"
Invoke-Gcloud @(
    "builds", "submit", ".",
    "--config=infrastructure/cloudbuild.yaml",
    "--ignore-file=.dockerignore",
    "--substitutions=_REGION=$Region,_REPOSITORY=$Repository,_TAG=$Tag"
)

Write-Host "[4/6] Deploying public demo API"
Invoke-Gcloud @(
    "run", "deploy", $apiService,
    "--image=$apiImage", "--region=$Region", "--platform=managed",
    "--allow-unauthenticated", "--port=8080", "--cpu=1", "--memory=1Gi",
    "--min-instances=0", "--max-instances=3",
    "--set-env-vars=MWANGAZA_ENV=demo,MWANGAZA_MODE=demo,MWANGAZA_API_DATA_MODE=demo,MWANGAZA_CACHE_REQUIRED=false",
    "--startup-probe=httpGet.path=/ready,initialDelaySeconds=0,timeoutSeconds=3,periodSeconds=5,failureThreshold=12",
    "--liveness-probe=httpGet.path=/health,initialDelaySeconds=10,timeoutSeconds=3,periodSeconds=30,failureThreshold=3"
)
$apiUrl = (& gcloud run services describe $apiService --region $Region --format="value(status.address.url)").Trim()
if (-not $apiUrl) { throw "Cloud Run did not return the API URL" }

Write-Host "[5/6] Deploying public web service"
Invoke-Gcloud @(
    "run", "deploy", $webService,
    "--image=$webImage", "--region=$Region", "--platform=managed",
    "--allow-unauthenticated", "--port=8080", "--cpu=1", "--memory=512Mi",
    "--min-instances=0", "--max-instances=3",
    "--set-env-vars=API_UPSTREAM=$apiUrl",
    "--startup-probe=httpGet.path=/healthz,initialDelaySeconds=0,timeoutSeconds=3,periodSeconds=5,failureThreshold=12",
    "--liveness-probe=httpGet.path=/healthz,initialDelaySeconds=5,timeoutSeconds=3,periodSeconds=30,failureThreshold=3"
)
$webUrl = (& gcloud run services describe $webService --region $Region --format="value(status.address.url)").Trim()
if (-not $webUrl) { throw "Cloud Run did not return the web URL" }

Write-Host "[6/6] Verifying public endpoints"
$webHealth = Invoke-WebRequest -UseBasicParsing -Uri "$webUrl/" -TimeoutSec 30
$apiHealth = Invoke-RestMethod -Uri "$webUrl/health" -TimeoutSec 30
$snapshot = Invoke-RestMethod -Uri "$webUrl/api/v1/snapshots/latest" -TimeoutSec 60
if ($webHealth.StatusCode -ne 200 -or $apiHealth.status -ne "ok" -or -not $snapshot.is_demo) {
    throw "Public smoke test failed"
}

Write-Host "Mwangaza public demo: $webUrl"
Write-Host "API service: $apiUrl"

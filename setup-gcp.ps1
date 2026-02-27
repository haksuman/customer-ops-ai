Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# =============================================================================
# setup-gcp.ps1 -- One-time GCP bootstrap for customer-ops-ai
#
# Run this ONCE before using deploy-backend.ps1 / deploy-frontend.ps1.
# It is idempotent -- safe to re-run if something fails mid-way.
#
# Prerequisites:
#   - Google Cloud SDK (gcloud) installed -> https://cloud.google.com/sdk/docs/install
#   - gcp.config.ps1 filled in (copy from gcp.config.ps1.example)
# =============================================================================

# --- Load config ---

$configFile = Join-Path $PSScriptRoot "gcp.config.ps1"
if (-not (Test-Path $configFile)) {
    Write-Host ""
    Write-Host "ERROR: gcp.config.ps1 not found." -ForegroundColor Red
    Write-Host "       Copy gcp.config.ps1.example to gcp.config.ps1 and fill in your values." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
. $configFile

# --- Helpers ---

function Invoke-GCloud {
    & gcloud @args
    $ec = $LASTEXITCODE
    if ($ec -ne 0) {
        Write-Host ""
        Write-Host "ERROR: gcloud $($args[0]) $($args[1]) failed (exit $ec)" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}

function Test-GCloud {
    $result = & gcloud @args 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return $result
}

# --- Validate ---

if (-not $PROJECT_ID -or $PROJECT_ID -eq "your-gcp-project-id") {
    Write-Host "ERROR: Set PROJECT_ID in gcp.config.ps1" -ForegroundColor Red; exit 1
}
if ($SERVICE_ACCOUNT_KEY_FILE -ne "" -and -not (Test-Path $SERVICE_ACCOUNT_KEY_FILE)) {
    Write-Host "ERROR: SERVICE_ACCOUNT_KEY_FILE not found: $SERVICE_ACCOUNT_KEY_FILE" -ForegroundColor Red; exit 1
}

# --- Header ---

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  GCP One-Time Setup -- $PROJECT_ID" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Project    : $PROJECT_ID"
Write-Host "  Region     : $REGION"
if ($SERVICE_ACCOUNT_KEY_FILE -ne "") {
    Write-Host "  Auth       : Service Account key"
} else {
    Write-Host "  Auth       : Personal account ($DEPLOYER_EMAIL)"
}
Write-Host ""

# --- [0/4] Authenticate ---

Write-Host "[0/4] Authenticating..." -ForegroundColor Yellow
if ($SERVICE_ACCOUNT_KEY_FILE -ne "") {
    Invoke-GCloud auth activate-service-account --key-file $SERVICE_ACCOUNT_KEY_FILE
    Write-Host "      Service account activated." -ForegroundColor Green
} else {
    $activeAccount = (& gcloud auth list --filter "status:ACTIVE" --format "value(account)" 2>$null).Trim()
    if ($activeAccount -eq $DEPLOYER_EMAIL) {
        Write-Host "      Already authenticated as $activeAccount -- OK" -ForegroundColor Green
    } else {
        Write-Host "      Opening browser to sign in as $DEPLOYER_EMAIL ..." -ForegroundColor Yellow
        Invoke-GCloud auth login $DEPLOYER_EMAIL
    }
}
Invoke-GCloud config set project $PROJECT_ID --quiet

# --- [1/4] Verify project ---

Write-Host "[1/4] Checking project '$PROJECT_ID'..." -ForegroundColor Yellow
$projectState = Test-GCloud projects describe $PROJECT_ID --format "value(lifecycleState)"
if ($projectState -eq "ACTIVE") {
    Write-Host "      Project exists and is ACTIVE -- OK" -ForegroundColor Green
} elseif ($null -eq $projectState) {
    Write-Host "      Project not found -- attempting to create..." -ForegroundColor DarkGray
    & gcloud projects create $PROJECT_ID --name "Customer Ops AI" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: Cannot create project '$PROJECT_ID'." -ForegroundColor Red
        Write-Host "  The project ID may already be taken globally." -ForegroundColor Yellow
        Write-Host "  Change PROJECT_ID in gcp.config.ps1 to a unique value." -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Host "      Project created." -ForegroundColor Green
} else {
    Write-Host "ERROR: Unexpected project state: $projectState" -ForegroundColor Red; exit 1
}

# --- [2/4] Enable APIs ---

Write-Host "[2/4] Enabling APIs (may take ~60 s the first time)..." -ForegroundColor Yellow
Invoke-GCloud services enable run.googleapis.com artifactregistry.googleapis.com --project $PROJECT_ID
Write-Host "      APIs enabled." -ForegroundColor Green

# --- [3/4] Create Artifact Registry repository ---

Write-Host "[3/4] Ensuring Artifact Registry repo '$AR_REPOSITORY' exists..." -ForegroundColor Yellow
$repoName = Test-GCloud artifacts repositories describe $AR_REPOSITORY `
    --location $REGION --project $PROJECT_ID --format "value(name)"
if ($null -ne $repoName -and $repoName -ne "") {
    Write-Host "      Repository already exists -- skipping." -ForegroundColor DarkGray
} else {
    Invoke-GCloud artifacts repositories create $AR_REPOSITORY `
        --repository-format docker `
        --location            $REGION `
        --description         "customer-ops-ai Docker images" `
        --project             $PROJECT_ID
    Write-Host "      Repository created." -ForegroundColor Green
}

# --- [4/4] Configure Docker credential helper ---

Write-Host "[4/4] Configuring Docker credential helper..." -ForegroundColor Yellow
Invoke-GCloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
Write-Host "      Docker auth configured." -ForegroundColor Green

# --- Done ---

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run:  .\deploy-backend.ps1"
Write-Host "     Copy the Backend URL it prints into BACKEND_URL in gcp.config.ps1."
Write-Host ""
Write-Host "  2. Run:  .\deploy-frontend.ps1"
Write-Host "     Copy the Frontend URL it prints into CORS_ALLOW_ORIGINS in gcp.config.ps1."
Write-Host ""
Write-Host "  3. Add secrets via GCP Console:"
Write-Host "     Cloud Run > customer-ops-backend > Edit and Deploy > Variables and Secrets"
Write-Host "       GEMINI_API_KEY"
Write-Host "       LANGCHAIN_API_KEY  (if tracing is enabled)"
Write-Host ""
Write-Host "  4. Run:  .\deploy-backend.ps1  (to apply the CORS restriction)"
Write-Host ""

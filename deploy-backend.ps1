Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# =============================================================================
# deploy-backend.ps1 -- Build and deploy the backend to Cloud Run
#
# Reads all environment-specific values from gcp.config.ps1.
# Run setup-gcp.ps1 once before the first deploy.
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

# --- App config (not environment-specific, safe to commit) ---

$SERVICE_NAME  = "customer-ops-backend"
$IMAGE_NAME    = "customer-ops-backend"
$PORT          = "8000"
$MEMORY        = "1Gi"
$CPU           = "1"
$MIN_INSTANCES = "0"
$MAX_INSTANCES = "1"
$TIMEOUT       = "120s"
$CONCURRENCY   = "10"

# Non-sensitive runtime env vars.
# Secrets (GEMINI_API_KEY, LANGCHAIN_API_KEY) are set once in the GCP Console:
#   Cloud Run > customer-ops-backend > Edit and Deploy > Variables and Secrets
$LLM_PROVIDER         = "gemini"
$GEMINI_MODEL         = "gemini-3-flash-preview"
$LANGCHAIN_TRACING_V2 = "false"

# --- Derived ---

$AR_HOST     = "$REGION-docker.pkg.dev"
$IMAGE_TAG   = "$AR_HOST/$PROJECT_ID/$AR_REPOSITORY/$IMAGE_NAME`:latest"
$BACKEND_DIR = Join-Path $PSScriptRoot "backend"

# --- Deploy ---

Write-Host ""
Write-Host "Deploying Backend to Cloud Run" -ForegroundColor Cyan
Write-Host "  Project : $PROJECT_ID  |  Region : $REGION  |  Service : $SERVICE_NAME"
Write-Host ""

Write-Host "[0/6] Authenticating..." -ForegroundColor Yellow
if ($SERVICE_ACCOUNT_KEY_FILE -ne "") {
    gcloud auth activate-service-account --key-file $SERVICE_ACCOUNT_KEY_FILE --quiet
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: SA auth failed" -ForegroundColor Red; exit 1 }
    Write-Host "      Service account activated." -ForegroundColor Green
} else {
    Write-Host "      Using active gcloud session." -ForegroundColor DarkGray
}

Write-Host "[1/6] Setting project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: could not set project" -ForegroundColor Red; exit 1 }

Write-Host "[2/6] Enabling APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com artifactregistry.googleapis.com --project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: could not enable APIs" -ForegroundColor Red; exit 1 }

Write-Host "[3/6] Ensuring Artifact Registry repository exists..." -ForegroundColor Yellow
gcloud artifacts repositories describe $AR_REPOSITORY --location $REGION --project $PROJECT_ID 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $AR_REPOSITORY `
        --repository-format docker `
        --location $REGION `
        --description "customer-ops-ai Docker images" `
        --project $PROJECT_ID
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: could not create AR repo" -ForegroundColor Red; exit 1 }
}

Write-Host "[4/6] Configuring Docker auth..." -ForegroundColor Yellow
gcloud auth configure-docker "$AR_HOST" --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: docker auth failed" -ForegroundColor Red; exit 1 }

Write-Host "[5/6] Building and pushing image..." -ForegroundColor Yellow
docker build --platform linux/amd64 -t "$IMAGE_TAG" "$BACKEND_DIR"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: docker build failed" -ForegroundColor Red; exit 1 }
docker push "$IMAGE_TAG"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: docker push failed" -ForegroundColor Red; exit 1 }

Write-Host "[6/6] Deploying to Cloud Run..." -ForegroundColor Yellow
$ENV_VARS = "LLM_PROVIDER=$LLM_PROVIDER,GEMINI_MODEL=$GEMINI_MODEL,CORS_ALLOW_ORIGINS=$CORS_ALLOW_ORIGINS,LANGCHAIN_TRACING_V2=$LANGCHAIN_TRACING_V2"

gcloud run deploy $SERVICE_NAME `
    --image           "$IMAGE_TAG" `
    --region          $REGION `
    --platform        managed `
    --allow-unauthenticated `
    --port            $PORT `
    --memory          $MEMORY `
    --cpu             $CPU `
    --min-instances   $MIN_INSTANCES `
    --max-instances   $MAX_INSTANCES `
    --timeout         $TIMEOUT `
    --concurrency     $CONCURRENCY `
    --update-env-vars "$ENV_VARS" `
    --project         $PROJECT_ID

if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Cloud Run deploy failed" -ForegroundColor Red; exit 1 }

$SERVICE_URL = gcloud run services describe $SERVICE_NAME `
    --region $REGION --project $PROJECT_ID --format "value(status.url)"

Write-Host ""
Write-Host "Backend URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""
Write-Host "If this is your first deploy, copy the URL above into BACKEND_URL in gcp.config.ps1" -ForegroundColor Yellow
Write-Host "then run deploy-frontend.ps1." -ForegroundColor Yellow
Write-Host ""

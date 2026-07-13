# TalkSense AI - Backend Startup Script (Diart Engine)
# Uses the experimental Diart Docker pipeline for speaker diarization.
# Requires: Docker Desktop running + talksense-diart-cpu image present.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uvicorn = Join-Path $scriptDir "venv\Scripts\uvicorn.exe"

if (-Not (Test-Path $uvicorn)) {
    Write-Error "uvicorn not found at $uvicorn. Please run: python -m venv venv && venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Verify Docker is reachable before starting
$dockerCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Docker is not running or not accessible." -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Verify the Diart image exists
$imageCheck = docker images talksense-diart-cpu --format "{{.Repository}}" 2>&1
if (-Not ($imageCheck -match "talksense-diart-cpu")) {
    Write-Host ""
    Write-Host "ERROR: Docker image 'talksense-diart-cpu' not found." -ForegroundColor Red
    Write-Host "Build it first with:  docker build -t talksense-diart-cpu ./experimental/diart/" -ForegroundColor Yellow
    exit 1
}

# Set engine selector + HF token
$env:DIARIZATION_ENGINE = "diart"

# Load HF_TOKEN from .env if not already set
if (-Not $env:HF_TOKEN) {
    $envFile = Join-Path $scriptDir ".env"
    if (Test-Path $envFile) {
        $hfLine = Select-String -Path $envFile -Pattern "^HF_TOKEN=" | Select-Object -First 1
        if ($hfLine) {
            $env:HF_TOKEN = $hfLine.Line.Split("=", 2)[1].Trim()
        }
    }
}

if (-Not $env:HF_TOKEN) {
    Write-Host "WARNING: HF_TOKEN not set. Diart may fail to download models on first run." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TalkSense AI — DIART ENGINE MODE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Diarization : Diart (Docker: talksense-diart-cpu)" -ForegroundColor Green
Write-Host " API docs    : http://localhost:8000/docs" -ForegroundColor Green
Write-Host " Health      : http://localhost:8000/health" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

& $uvicorn main:app --reload --host 0.0.0.0 --port 8000

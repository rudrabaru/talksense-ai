# TalkSense AI - Backend Startup Script (Variant C Engine)
# Uses the production Pyannote + embedding Variant C pipeline for speaker diarization.
# This is the canonical production configuration.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uvicorn = Join-Path $scriptDir "venv\Scripts\uvicorn.exe"

if (-Not (Test-Path $uvicorn)) {
    Write-Error "uvicorn not found at $uvicorn. Please run: python -m venv venv && venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Set engine selector explicitly (variant_c is also the default if unset)
$env:DIARIZATION_ENGINE = "variant_c"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TalkSense AI — VARIANT C ENGINE MODE (Production)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Diarization : Pyannote + Speaker Embeddings (Variant C)" -ForegroundColor Green
Write-Host " API docs    : http://localhost:8000/docs" -ForegroundColor Green
Write-Host " Health      : http://localhost:8000/health" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

& $uvicorn main:app --reload --host 0.0.0.0 --port 8000

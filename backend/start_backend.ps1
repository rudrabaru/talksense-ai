# TalkSense AI - Backend Startup Script
# Always use this script to start the backend (ensures correct venv is used)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$uvicorn = Join-Path $scriptDir "venv\Scripts\uvicorn.exe"

if (-Not (Test-Path $uvicorn)) {
    Write-Error "uvicorn not found at $uvicorn. Please run: python -m venv venv && venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting TalkSense AI backend with venv Python..." -ForegroundColor Cyan
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health:   http://localhost:8000/health" -ForegroundColor Green
Write-Host ""

& $uvicorn main:app --reload --host 0.0.0.0 --port 8000

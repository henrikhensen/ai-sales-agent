# Run backend and frontend locally (no Docker), each in its own window.
# Requires: .venv already created with requirements.txt installed, and
# Postgres/Redis reachable (e.g. via `docker compose up postgres redis`).
#
# Usage:  powershell -File scripts\dev.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "No .venv found at $venvPython" -ForegroundColor Yellow
    Write-Host "Create it first:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip.exe install -r requirements.txt"
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "No .env found — copying .env.example to .env" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

$frontendModules = Join-Path $repoRoot "frontend\node_modules"
if (-not (Test-Path $frontendModules)) {
    Write-Host "Installing frontend dependencies (first run)..." -ForegroundColor Cyan
    Push-Location (Join-Path $repoRoot "frontend")
    npm install
    Pop-Location
}

Write-Host "Starting backend (uvicorn --reload) in a new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$repoRoot'; & '$venvPython' -m uvicorn backend.main:app --reload"
)

Write-Host "Starting frontend (npm run dev) in a new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$repoRoot\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Reminder: Postgres and Redis must be reachable (POSTGRES_HOST / REDIS_HOST" -ForegroundColor Yellow
Write-Host "in .env set to 'localhost'), e.g. via: docker compose up postgres redis -d"
Write-Host ""
Write-Host "Backend  : http://localhost:8000/docs"
Write-Host "Frontend : http://localhost:3000"

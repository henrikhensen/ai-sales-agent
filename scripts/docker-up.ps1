# Build and start the full stack (backend, frontend, postgres, redis) via
# Docker Compose, then print the URLs to open.
#
# Usage:  powershell -File scripts\docker-up.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".env")) {
    Write-Host "No .env found — copying .env.example to .env" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

try {
    docker version | Out-Null
} catch {
    Write-Host "Docker does not appear to be running. Start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host "Building and starting containers..." -ForegroundColor Cyan
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Stack is starting. Once healthy:" -ForegroundColor Green
Write-Host "  Backend health : http://localhost:8000/api/v1/health"
Write-Host "  Swagger docs   : http://localhost:8000/docs"
Write-Host "  Frontend       : http://localhost:3000"
Write-Host ""
Write-Host "View logs with: docker compose logs -f"

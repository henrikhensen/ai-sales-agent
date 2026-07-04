# Stop and remove the Docker Compose stack (containers + network). Named
# volumes (postgres_data, redis_data) are kept so data survives a restart.
#
# Usage:  powershell -File scripts\docker-down.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Stopping containers..." -ForegroundColor Cyan
docker compose down
exit $LASTEXITCODE

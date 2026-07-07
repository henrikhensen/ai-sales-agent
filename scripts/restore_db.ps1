# Restore a PostgreSQL backup (created by backup_db.ps1) into the running
# sales_agent_postgres Docker container.
#
# DESTRUCTIVE: overwrites all data currently in the target database. Asks
# for explicit confirmation before doing anything.
#
# Usage:  powershell -File scripts\restore_db.ps1 -BackupFile .\backups\sales_agent_20260101_120000.sql

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Get-DotEnvValue {
    param([string]$Name, [string]$Default)
    if (-not (Test-Path ".env")) { return $Default }
    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -Last 1
    if (-not $line) { return $Default }
    $value = ($line -split "=", 2)[1].Trim()
    $value = $value.Trim('"').Trim("'")
    if ([string]::IsNullOrEmpty($value)) { return $Default }
    return $value
}

if (-not (Test-Path $BackupFile)) {
    Write-Host "Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

$postgresUser = Get-DotEnvValue "POSTGRES_USER" "sales_agent"
$postgresDb = Get-DotEnvValue "POSTGRES_DB" "sales_agent"
$postgresPassword = Get-DotEnvValue "POSTGRES_PASSWORD" ""
$containerName = "sales_agent_postgres"

$running = docker ps --format "{{.Names}}" | Select-String -SimpleMatch $containerName
if (-not $running) {
    Write-Host "Container '$containerName' is not running. Start it with 'docker compose up -d postgres' first." -ForegroundColor Red
    exit 1
}

Write-Host "WARNING: This will overwrite ALL data in database '$postgresDb' with the contents of $BackupFile." -ForegroundColor Yellow
Write-Host "This cannot be undone unless you have another backup of the current data." -ForegroundColor Yellow
$confirmation = Read-Host "Type 'yes' to continue"
if ($confirmation -ne "yes") {
    Write-Host "Aborted. No changes were made." -ForegroundColor Cyan
    exit 1
}

Write-Host "Restoring $BackupFile into database '$postgresDb' ..." -ForegroundColor Cyan
Get-Content $BackupFile -Raw | docker exec -i -e "PGPASSWORD=$postgresPassword" $containerName `
    psql -U $postgresUser -d $postgresDb

if ($LASTEXITCODE -ne 0) {
    Write-Host "Restore failed (psql exited with code $LASTEXITCODE). Check the output above for details." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Restore complete." -ForegroundColor Green

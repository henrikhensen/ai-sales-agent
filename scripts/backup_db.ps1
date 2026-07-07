# Create a timestamped PostgreSQL backup from the running
# sales_agent_postgres Docker container (plain-SQL pg_dump), and prune
# backups older than BACKUP_RETENTION_DAYS. Reads POSTGRES_USER,
# POSTGRES_DB, POSTGRES_PASSWORD, BACKUP_DIR, and BACKUP_RETENTION_DAYS
# from .env — never prints the password.
#
# Usage:  powershell -File scripts\backup_db.ps1

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

$postgresUser = Get-DotEnvValue "POSTGRES_USER" "sales_agent"
$postgresDb = Get-DotEnvValue "POSTGRES_DB" "sales_agent"
$postgresPassword = Get-DotEnvValue "POSTGRES_PASSWORD" ""
$backupDir = Get-DotEnvValue "BACKUP_DIR" "./backups"
$retentionDays = [int](Get-DotEnvValue "BACKUP_RETENTION_DAYS" "7")
$containerName = "sales_agent_postgres"

$running = docker ps --format "{{.Names}}" | Select-String -SimpleMatch $containerName
if (-not $running) {
    Write-Host "Container '$containerName' is not running. Start it with 'docker compose up -d postgres' first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $backupDir "${postgresDb}_${timestamp}.sql"

Write-Host "Backing up database '$postgresDb' to $backupFile ..." -ForegroundColor Cyan
docker exec -e "PGPASSWORD=$postgresPassword" $containerName `
    pg_dump -U $postgresUser -d $postgresDb --clean --if-exists | Out-File -FilePath $backupFile -Encoding utf8

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backup failed (pg_dump exited with code $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}

$sizeKb = [math]::Round((Get-Item $backupFile).Length / 1KB, 1)
Write-Host "Backup complete: $backupFile ($sizeKb KB)" -ForegroundColor Green

if ($retentionDays -gt 0) {
    Write-Host "Removing backups older than $retentionDays day(s) in $backupDir ..." -ForegroundColor Cyan
    $cutoff = (Get-Date).AddDays(-$retentionDays)
    Get-ChildItem -Path $backupDir -Filter "${postgresDb}_*.sql" |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Write-Host "  removing $($_.Name)" -ForegroundColor DarkGray
            Remove-Item $_.FullName -Force
        }
}

Write-Host "Done." -ForegroundColor Green

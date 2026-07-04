# Run the backend test suite using the project's local virtual environment.
#
# Usage:  powershell -File scripts\test.ps1

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

Write-Host "Running backend tests..." -ForegroundColor Cyan
& $venvPython -m pytest -q
exit $LASTEXITCODE

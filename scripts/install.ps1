# install.ps1 - Installer for ops-lite Antigravity plugin

[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Antigravity 2.0 ops-lite Plugin Installer " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path

Write-Host "[1/5] Checking Prerequisites..." -ForegroundColor Yellow

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python not found in PATH. Please install Python 3.10+ and re-run."
    exit 1
}
$pyVer = & python --version
Write-Host "  Found $pyVer" -ForegroundColor Green

# 2. Check agy CLI
$agyCmd = Get-Command agy -ErrorAction SilentlyContinue
if (-not $agyCmd) {
    Write-Warning "agy CLI not found in PATH. MCP server can still be run standalone, but plugin auto-registration requires agy."
} else {
    Write-Host "  Found agy CLI: $($agyCmd.Source)" -ForegroundColor Green
}

# 3. Setup Virtual Environment
Write-Host "[2/5] Setting up dedicated Python virtual environment..." -ForegroundColor Yellow
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "  Creating venv at $VenvDir..."
    & python -m venv $VenvDir
}

Write-Host "  Installing dependencies..."
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet "mcp>=2.3.0" pytest

# 4. Generate dynamic mcp_config.json
Write-Host "[3/5] Configuring MCP server paths..." -ForegroundColor Yellow
$ServerDir = Join-Path $ProjectRoot "server"
$escapedVenvPython = $VenvPython.Replace('\', '\\')
$escapedServerDir = $ServerDir.Replace('\', '\\')

$mcpConfigContent = @"
{
  "mcpServers": {
    "ops-lite": {
      "command": "$escapedVenvPython",
      "args": [
        "-m",
        "ops_lite.server"
      ],
      "env": {
        "PYTHONPATH": "$escapedServerDir"
      }
    }
  }
}
"@
Set-Content -Path (Join-Path $ProjectRoot "mcp_config.json") -Value $mcpConfigContent -Encoding UTF8
Write-Host "  mcp_config.json updated successfully." -ForegroundColor Green

# 5. Run Validation & Tests
if (-not $SkipTests) {
    Write-Host "[4/5] Running automated tests..." -ForegroundColor Yellow
    & $VenvPython -m pytest (Join-Path $ServerDir "tests") -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tests failed. Installation aborted."
        exit 1
    }
    Write-Host "  All tests passed." -ForegroundColor Green
}

# 6. Validate and Install Plugin
Write-Host "[5/5] Registering plugin with Antigravity..." -ForegroundColor Yellow
if ($agyCmd) {
    & agy plugin validate $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Plugin validation failed."
        exit 1
    }
    
    & agy plugin install $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Error "agy plugin install failed."
        exit 1
    }
    Write-Host "  Plugin successfully installed to global Antigravity registry!" -ForegroundColor Green
} else {
    Write-Warning "Skipped agy install due to missing CLI. Plugin files are ready."
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Installation Complete! " -ForegroundColor Green
Write-Host " ops-lite is now active with 5 token-saving tools:" -ForegroundColor White
Write-Host "  - ops_summary" -ForegroundColor Gray
Write-Host "  - ops_search" -ForegroundColor Gray
Write-Host "  - ops_read" -ForegroundColor Gray
Write-Host "  - ops_run" -ForegroundColor Gray
Write-Host "  - ops_result" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan

# uninstall.ps1 - Uninstaller for ops-lite Antigravity plugin

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Antigravity 2.0 ops-lite Plugin Uninstaller " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$agyCmd = Get-Command agy -ErrorAction SilentlyContinue

if ($agyCmd) {
    Write-Host "Uninstalling ops-lite via agy CLI..." -ForegroundColor Yellow
    try {
        & agy plugin uninstall ops-lite
        Write-Host "  agy plugin uninstall ops-lite completed." -ForegroundColor Green
    } catch {
        Write-Warning "agy uninstall returned: $_"
    }
}

# Verify plugin removal from config/plugins
$UserConfigPlugins = Join-Path $env:USERPROFILE ".gemini\config\plugins\ops-lite"
if (Test-Path $UserConfigPlugins) {
    Write-Host "Removing residual plugin directory at $UserConfigPlugins..." -ForegroundColor Yellow
    Remove-Item -Path $UserConfigPlugins -Recurse -Force
    Write-Host "  Residual files removed." -ForegroundColor Green
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " ops-lite has been cleanly uninstalled. " -ForegroundColor Green
Write-Host " No user files or other plugins were modified. " -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan

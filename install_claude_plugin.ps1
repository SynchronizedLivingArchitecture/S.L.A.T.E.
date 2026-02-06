# SLATE Claude Code Plugin Installer (PowerShell)
# Registers SLATE as a Claude Code plugin with skills and MCP tools

param(
    [switch]$Uninstall,
    [switch]$Validate
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "SLATE Claude Code Plugin Installer" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Check Python venv
$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python venv not found at $PythonExe" -ForegroundColor Red
    Write-Host "Please run the SLATE installer first to create the venv." -ForegroundColor Yellow
    exit 1
}

# Build arguments
$Args = @()
if ($Uninstall) { $Args += "--uninstall" }
if ($Validate) { $Args += "--validate" }

# Run installer
& $PythonExe (Join-Path $ScriptDir "install_claude_plugin.py") @Args

if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done! The SLATE plugin is now available in Claude Code." -ForegroundColor Green
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  1. Open Claude Code in this directory"
Write-Host "  2. Type /slate-help to see available commands"
Write-Host "  3. Type /slate start to launch SLATE services"

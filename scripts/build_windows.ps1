# Build script for Windows: creates a venv, installs requirements, and builds a single EXE with PyInstaller
# Usage (PowerShell):
#   .\scripts\build_windows.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root\..  # change to repo root

Write-Host "Building Digital-Trackpad (single EXE)" -ForegroundColor Cyan

# Create venv if missing
if (-not (Test-Path .venv)) {
    python -m venv .venv
}

# Activate venv
$activate = Join-Path (Resolve-Path .venv) "Scripts\Activate.ps1"
Write-Host "Activating venv: $activate"
. $activate

# Upgrade pip and install needed packages
# Use the venv python executable to avoid stale pip launchers
$venvPython = Join-Path (Resolve-Path .venv) "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Python executable not found in venv: $venvPython"
    exit 1
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt pyinstaller

# Build flags
$templates = "templates;templates"
$static = "static;static"
$iconPath = "assets\app.ico"
# Prepare argument list to avoid quoting issues
$pyArgs = @("--clean", "--onefile", "--noconsole", "--add-data", $templates, "--add-data", $static)
if (Test-Path $iconPath) {
    $pyArgs += "--icon"
    $pyArgs += $iconPath
    Write-Host "Using icon: $iconPath"
} else {
    Write-Host "No icon found at assets\app.ico; continuing without icon"
}

# Add entry script
$pyArgs += "app.py"

Write-Host "Running: pyinstaller $($pyArgs -join ' ')"
& $venvPython -m PyInstaller @pyArgs

Write-Host "Build finished. Output in dist" -ForegroundColor Green
Write-Host "If you used --onefile, dist\app.exe will be your single EXE (name may match script name)."

Write-Host "Tip: If the executable can't find templates/static at runtime, ensure the app.py PyInstaller _MEIPASS handling is present (already added to app.py)."
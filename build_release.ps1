# build_release.ps1 — Automated Nuitka Native Build & Release Sync Script
# Aero Automotive Suite — Dongfeng Shine Edition
# Developed by Abdelrhman Hamdy - Senior Software Engineer

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Aero Suite: Compiling Native Binary via Nuitka..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "src;."

$nuitkaArgs = @(
    "-m", "nuitka",
    "--onefile",
    "--windows-console-mode=disable",
    "--enable-plugin=tk-inter",
    "--include-package-data=customtkinter",
    "--include-package-data=PIL",
    "--include-package=cryptography",
    "--include-module=app_gui",
    "--include-module=theme",
    "--include-module=payload_engine",
    "--include-module=apk_engine",
    "--include-module=usb_detector",
    "--include-module=sync_manager",
    "--output-dir=nuitka_dist",
    "--output-filename=AeroSuite_Native.exe",
    "--assume-yes-for-downloads",
    "--jobs=10",
    "main.py"
)

& python $nuitkaArgs

Write-Host "[OK] Nuitka compilation finished successfully!" -ForegroundColor Green

# Stop any running process
Get-Process -Name 'AeroSuite', 'AeroSuite_Native' -ErrorAction SilentlyContinue | Stop-Process -Force

# Deploy to root
Copy-Item -Path "nuitka_dist\AeroSuite_Native.exe" -Destination "AeroSuite.exe" -Force
Write-Host "[OK] Deployed to AeroSuite.exe" -ForegroundColor Green

# Sync to Release folder
$releaseDir = "D:\Work\Projects\Aero\Aero_Suite\AeroSuite_v1.0_Beta"
if (Test-Path -Path $releaseDir) {
    Copy-Item -Path "nuitka_dist\AeroSuite_Native.exe" -Destination "$releaseDir\AeroSuite.exe" -Force
    Write-Host "[OK] Synced to AeroSuite_v1.0_Beta\AeroSuite.exe" -ForegroundColor Green
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Release build is complete and fully protected!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

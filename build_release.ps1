# build_release.ps1 — Automated Build & Release Sync Script
# Aero Automotive Suite — Dongfeng Shine Edition (Version 1.1 Beta)
# Developed & Maintained by Abdelrhman Hamdy - Senior Software Engineer

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Aero Suite v1.1 Beta: Compiling Standalone Protected Release..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Stop any running AeroSuite process
Get-Process -Name 'AeroSuite' -ErrorAction SilentlyContinue | Stop-Process -Force

# Clean old artifacts
Remove-Item -Path "dist", "build" -Recurse -Force -ErrorAction SilentlyContinue

# Execute PyInstaller Build
$env:PYTHONPATH = "src;."
& python -m PyInstaller --clean --noconfirm AeroSuite.spec

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "[OK] Executable compiled successfully!" -ForegroundColor Green

# Deploy to root
Copy-Item -Path "dist\AeroSuite.exe" -Destination "AeroSuite.exe" -Force
Write-Host "[OK] Deployed to root AeroSuite.exe" -ForegroundColor Green

# Setup and sync AeroSuite_v1.1_Beta release folder
$releaseDir = "D:\Work\Projects\Aero\Aero_Suite\AeroSuite_v1.1_Beta"
if (-not (Test-Path -Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
}

# Copy compiled executable
Copy-Item -Path "dist\AeroSuite.exe" -Destination "$releaseDir\AeroSuite.exe" -Force
Write-Host "[OK] Synced AeroSuite.exe to $releaseDir" -ForegroundColor Green

# Copy ADB tools & runtime DLLs
Copy-Item -Path "adb.exe" -Destination "$releaseDir\adb.exe" -Force
Copy-Item -Path "AdbWinApi.dll" -Destination "$releaseDir\AdbWinApi.dll" -Force
Copy-Item -Path "AdbWinUsbApi.dll" -Destination "$releaseDir\AdbWinUsbApi.dll" -Force
Write-Host "[OK] Synced ADB binaries & DLLs" -ForegroundColor Green

# Copy Release Instructions
if (Test-Path -Path "README_INSTRUCTIONS_v1.1_Beta.txt") {
    Copy-Item -Path "README_INSTRUCTIONS_v1.1_Beta.txt" -Destination "$releaseDir\README_INSTRUCTIONS_v1.1_Beta.txt" -Force
    Write-Host "[OK] Synced README_INSTRUCTIONS_v1.1_Beta.txt" -ForegroundColor Green
}

# Ensure folders exist
$subDirs = @("backups", "logs")
foreach ($sub in $subDirs) {
    $targetPath = Join-Path $releaseDir $sub
    if (-not (Test-Path -Path $targetPath)) {
        New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
    }
}

# Sync APKs directory
Write-Host "Syncing APKs..." -ForegroundColor Cyan
robocopy "apks" "$releaseDir\apks" /E /XO /NP /R:2 /W:2 | Out-Null

# Sync FactoryBackup directory
Write-Host "Syncing FactoryBackup..." -ForegroundColor Cyan
robocopy "FactoryBackup" "$releaseDir\FactoryBackup" /E /XO /NP /R:2 /W:2 | Out-Null

# Sync Assets directory
Write-Host "Syncing Assets..." -ForegroundColor Cyan
robocopy "assets" "$releaseDir\assets" /E /XO /NP /R:2 /W:2 | Out-Null

# Sync Locales directory
Write-Host "Syncing Locales..." -ForegroundColor Cyan
robocopy "src\locales" "$releaseDir\locales" /E /XO /NP /R:2 /W:2 | Out-Null

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Release v1.1 Beta is complete, fully packaged and ready for testers!" -ForegroundColor Green
Write-Host "Location: $releaseDir" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

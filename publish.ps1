# VoicePilot AI Self-Contained Publishing and MSI Installer Generation Script
param(
    [string]$Configuration = "Release",
    [string]$Runtime = "win-x64",
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " VoicePilot AI - Publish & Packaging" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$root = (Get-Item .).FullName
$publishDir = Join-Path $root "publish\$Runtime"
$installerDir = Join-Path $root "installer"
$msiOutput = Join-Path $installerDir "VoicePilot-Setup-$Version.msi"

Write-Host "`n[1/3] Publishing self-contained executable ($Runtime)..." -ForegroundColor Yellow
dotnet publish src/VoicePilot.App/VoicePilot.App.csproj -c $Configuration -r $Runtime --self-contained true -o $publishDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "Self-contained publish failed!"
    exit $LASTEXITCODE
}
Write-Host "Self-contained executable published to: $publishDir\VoicePilot.exe" -ForegroundColor Green

Write-Host "`n[2/3] Checking WiX 7 compiler tool..." -ForegroundColor Yellow
if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
    Write-Host "Installing WiX toolset..." -ForegroundColor Cyan
    dotnet tool install --global wix
}

Write-Host "`n[3/3] Compiling WiX 7 MSI Windows Installer..." -ForegroundColor Yellow
if (-not (Test-Path $installerDir)) {
    New-Item -ItemType Directory -Force -Path $installerDir | Out-Null
}

wix build -arch x64 -d PublishDir="$publishDir" src/VoicePilot.Installer/Package.wxs -o $msiOutput
if ($LASTEXITCODE -ne 0) {
    Write-Error "MSI packaging failed!"
    exit $LASTEXITCODE
}

$msiFile = Get-Item $msiOutput
$msiSizeMb = [math]::Round($msiFile.Length / 1MB, 2)
Write-Host "`n==========================================" -ForegroundColor Green
Write-Host " Packaging Succeeded!" -ForegroundColor Green
Write-Host " Standalone Executable: $publishDir\VoicePilot.exe" -ForegroundColor Green
Write-Host " Windows Installer:     $msiOutput ($msiSizeMb MB)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

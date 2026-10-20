# VoicePilot AI Build and Test Automation Script
param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " VoicePilot AI - Build & Test Pipeline" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n[1/2] Restoring and Building Solution ($Configuration)..." -ForegroundColor Yellow
dotnet build VoicePilot.sln -c $Configuration
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    exit $LASTEXITCODE
}
Write-Host "Build completed successfully." -ForegroundColor Green

Write-Host "`n[2/2] Running Unit & Integration Tests..." -ForegroundColor Yellow
dotnet test tests/VoicePilot.Tests/VoicePilot.Tests.csproj -c $Configuration --no-build --logger "console;verbosity=normal"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tests failed!"
    exit $LASTEXITCODE
}
Write-Host "`nAll test suites passed successfully!" -ForegroundColor Green

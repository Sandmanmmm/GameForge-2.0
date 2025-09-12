# GameForge AI - Migration Guide and Quick Reference
# This script provides guidance on using the migration tools

Write-Host "📖 GameForge AI - Migration Guide" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

Write-Host "`n🎯 MIGRATION OVERVIEW" -ForegroundColor Magenta
Write-Host "This migration transforms your repository into an enterprise-grade structure" -ForegroundColor White
Write-Host "that rivals HeyBossAI and Rosebud AI platforms." -ForegroundColor White

Write-Host "`n📋 AVAILABLE SCRIPTS" -ForegroundColor Magenta
Write-Host "1. migrate-to-production-complete.ps1  - One-click complete migration" -ForegroundColor Green
Write-Host "2. migrate-to-production-structure.ps1 - Detailed migration script" -ForegroundColor Green  
Write-Host "3. validate-production-structure.ps1   - Structure validation" -ForegroundColor Green
Write-Host "4. migration-guide.ps1                 - This help script" -ForegroundColor Green

Write-Host "`n🚀 QUICK START" -ForegroundColor Magenta
Write-Host "For most users, run the complete migration:" -ForegroundColor White
Write-Host "   .\scripts\migrate-to-production-complete.ps1 -Execute" -ForegroundColor Cyan

Write-Host "`n🔍 SAFE APPROACH (Recommended)" -ForegroundColor Magenta
Write-Host "1. First, run a dry-run to see what will happen:" -ForegroundColor White
Write-Host "   .\scripts\migrate-to-production-complete.ps1" -ForegroundColor Cyan
Write-Host "2. Review the planned changes" -ForegroundColor White
Write-Host "3. Execute the migration:" -ForegroundColor White
Write-Host "   .\scripts\migrate-to-production-complete.ps1 -Execute" -ForegroundColor Cyan
Write-Host "4. Validate the results:" -ForegroundColor White
Write-Host "   .\scripts\validate-production-structure.ps1 -Detailed" -ForegroundColor Cyan

Write-Host "`n Ready to compete with industry leaders!" -ForegroundColor Green
Write-Host "Your GameForge AI repository will be enterprise-ready." -ForegroundColor Green

$choice = Read-Host "`nWould you like to start the migration now? (y/N)"
if ($choice -eq 'y' -or $choice -eq 'Y') {
    Write-Host "`n🚀 Starting migration..." -ForegroundColor Cyan
    $scriptPath = Join-Path $PSScriptRoot "migrate-to-production-complete.ps1"
    if (Test-Path $scriptPath) {
        & $scriptPath
    } else {
        Write-Host "❌ Migration script not found. Please ensure you are in the scripts directory." -ForegroundColor Red
    }
} else {
    Write-Host "`n💡 Run the migration when you are ready:" -ForegroundColor Blue
    Write-Host "   .\scripts\migrate-to-production-complete.ps1 -Execute" -ForegroundColor Cyan
}
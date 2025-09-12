# GameForge Development Startup Script
Write-Host " Starting GameForge Development Environment" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# Navigate to project directory
Set-Location "D:\GameForge\ai-game-production-p"

# Show disk space
Write-Host "`n Current disk space:" -ForegroundColor Cyan
Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DeviceID -eq "D:"} | ForEach-Object {
    $freeGB = [math]::Round($_.FreeSpace/1GB, 2)
    Write-Host "   D: drive - $freeGB GB free" -ForegroundColor White
}

Write-Host "`n GameForge development environment ready!" -ForegroundColor Green
Write-Host " Working directory: D:\GameForge\ai-game-production-p" -ForegroundColor Yellow
Write-Host " GitHub: https://github.com/Sandmanmmm/ai-game-production-p" -ForegroundColor Cyan

Write-Host "`n Available commands:" -ForegroundColor Cyan
Write-Host "   npm run dev          - Start frontend development server" -ForegroundColor White
Write-Host "   docker-compose up    - Start backend services" -ForegroundColor White
Write-Host "   kubectl get pods     - Check Kubernetes cluster" -ForegroundColor White
Write-Host "   git status           - Check repository status" -ForegroundColor White

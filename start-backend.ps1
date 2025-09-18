# GameForge Backend Server Startup Script
# Start the server in a separate window

param(
    [string]$Port = "8080"
)

Write-Host "Starting GameForge Backend Server..." -ForegroundColor Green
Write-Host "Port: $Port" -ForegroundColor Yellow

# Start server in new PowerShell window
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m uvicorn gameforge.app:app --host 0.0.0.0 --port $Port --reload"

Start-Sleep -Seconds 5

# Test if server is responding
try {
    Write-Host "Testing server response..." -ForegroundColor Yellow
    $Response = Invoke-RestMethod -Uri "http://localhost:$Port/health" -TimeoutSec 10
    Write-Host "Server started successfully! Status: $($Response.status)" -ForegroundColor Green
    Write-Host "Server URL: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "API Docs: http://localhost:$Port/docs" -ForegroundColor Cyan
} catch {
    Write-Host "Server may still be starting up..." -ForegroundColor Yellow
    Write-Host "Check the server window for startup progress" -ForegroundColor Yellow
}

Write-Host "Server is running in a separate window. Close that window to stop the server." -ForegroundColor Green
#
# GameForge Backend Server Startup Script
# =======================================
#
# This script starts the GameForge FastAPI backend server in a new PowerShell window
# to prevent it from being terminated when other terminal commands are run.
#

param(
    [string]$Port = "8080",
    [string]$Host = "0.0.0.0",
    [switch]$Reload,
    [switch]$Development
)

# Set script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"

Write-Host "🚀 GameForge Backend Server Startup" -ForegroundColor $Cyan
Write-Host "=====================================" -ForegroundColor $Cyan

# Check if server is already running
$ExistingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "python"
}

if ($ExistingProcess) {
    Write-Host "⚠️  Server already running on PID: $($ExistingProcess.Id)" -ForegroundColor $Yellow
    $Choice = Read-Host "Kill existing server and start new one? (y/N)"
    if ($Choice -eq "y" -or $Choice -eq "Y") {
        Stop-Process -Id $ExistingProcess.Id -Force
        Start-Sleep -Seconds 2
        Write-Host "✅ Existing server terminated" -ForegroundColor $Green
    } else {
        Write-Host "❌ Startup cancelled" -ForegroundColor $Red
        exit 1
    }
}

# Prepare environment
Write-Host "📋 Preparing environment..." -ForegroundColor $Yellow

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "🐍 Activating virtual environment..." -ForegroundColor $Yellow
    $PythonCmd = ".\venv\Scripts\python.exe"
} else {
    Write-Host "🐍 Using system Python..." -ForegroundColor $Yellow
    $PythonCmd = "python"
}

# Build uvicorn command
$UvicornArgs = @(
    "-m", "uvicorn", 
    "gameforge.app:app",
    "--host", $Host,
    "--port", $Port
)

if ($Reload) {
    $UvicornArgs += "--reload"
}

if ($Development) {
    $UvicornArgs += "--log-level", "debug"
}

$Command = "$PythonCmd $($UvicornArgs -join ' ')"

Write-Host "🎯 Server configuration:" -ForegroundColor $Cyan
Write-Host "   Host: $Host" -ForegroundColor $White
Write-Host "   Port: $Port" -ForegroundColor $White
Write-Host "   Reload: $Reload" -ForegroundColor $White
Write-Host "   Development: $Development" -ForegroundColor $White
Write-Host "   Command: $Command" -ForegroundColor $White

# Start server in new window
Write-Host "`n🚀 Starting server in new window..." -ForegroundColor $Green

try {
    $ProcessInfo = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-Command", 
        "cd '$ScriptDir'; Write-Host 'GameForge Backend Server' -ForegroundColor Green; Write-Host 'Window can be closed to stop server' -ForegroundColor Yellow; $Command"
    ) -PassThru
    
    Start-Sleep -Seconds 3
    
    # Check if process is still running
    if (Get-Process -Id $ProcessInfo.Id -ErrorAction SilentlyContinue) {
        Write-Host "✅ Server started successfully!" -ForegroundColor $Green
        Write-Host "   PID: $($ProcessInfo.Id)" -ForegroundColor $White
        Write-Host "   URL: http://$Host`:$Port" -ForegroundColor $White
        Write-Host "   Health: http://$Host`:$Port/health" -ForegroundColor $White
        Write-Host "   Docs: http://$Host`:$Port/docs" -ForegroundColor $White
        
        # Test server response
        Write-Host "`n🔍 Testing server response..." -ForegroundColor $Yellow
        Start-Sleep -Seconds 5
        
        try {
            $Response = Invoke-RestMethod -Uri "http://$Host`:$Port/health" -TimeoutSec 10
            Write-Host "✅ Server responding: $($Response.status)" -ForegroundColor $Green
        } catch {
            Write-Host "⚠️  Server not responding yet (may still be starting up)" -ForegroundColor $Yellow
        }
        
    } else {
        Write-Host "❌ Server failed to start" -ForegroundColor $Red
        exit 1
    }
    
} catch {
    Write-Host "❌ Failed to start server: $($_.Exception.Message)" -ForegroundColor $Red
    exit 1
}

Write-Host "`n🎉 Server startup complete!" -ForegroundColor $Green
Write-Host "   The server is running in a separate window" -ForegroundColor $White
Write-Host "   Close that window to stop the server" -ForegroundColor $White
Write-Host "   This terminal can be used for other commands" -ForegroundColor $White
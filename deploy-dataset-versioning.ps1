# GameForge Dataset Versioning (DVC) Deployment Script
# ==================================================
# This script deploys the complete Dataset Versioning system
# with DVC integration, data validation, and drift detection

param(
    [switch]$Build = $false,
    [switch]$Deploy = $false,
    [switch]$Test = $false,
    [switch]$Stop = $false,
    [switch]$Logs = $false,
    [switch]$Clean = $false,
    [string]$Environment = "production"
)

$ErrorActionPreference = "Stop"

# Configuration
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $SCRIPT_DIR)
$COMPOSE_FILE = "$PROJECT_ROOT/docker/compose/docker-compose.production-hardened.yml"
$ENV_FILE = "$PROJECT_ROOT/docker/compose/.env"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

Write-Info "=========================================="
Write-Info "GameForge Dataset Versioning Deployment"
Write-Info "=========================================="

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "✓ Docker found: $dockerVersion"
    } catch {
        Write-Error "✗ Docker not found. Please install Docker Desktop."
        exit 1
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version
        Write-Success "✓ Docker Compose found: $composeVersion"
    } catch {
        Write-Error "✗ Docker Compose not found. Please install Docker Compose."
        exit 1
    }
    
    # Check compose file
    if (-not (Test-Path $COMPOSE_FILE)) {
        Write-Error "✗ Compose file not found: $COMPOSE_FILE"
        exit 1
    }
    Write-Success "✓ Compose file found"
    
    # Check environment file
    if (-not (Test-Path $ENV_FILE)) {
        Write-Warning "⚠ Environment file not found. Creating default..."
        Copy-Item "$PROJECT_ROOT/docker/compose/.env.example" $ENV_FILE -ErrorAction SilentlyContinue
    }
    Write-Success "✓ Environment file ready"
}

# Create required directories
function Initialize-Directories {
    Write-Info "Creating required directories..."
    
    $directories = @(
        "$PROJECT_ROOT/ml-platform/data",
        "$PROJECT_ROOT/volumes/dataset-cache",
        "$PROJECT_ROOT/volumes/dvc-cache",
        "$PROJECT_ROOT/logs/dataset-api"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Success "✓ Created directory: $dir"
        }
    }
}

# Build services
function Build-Services {
    Write-Info "Building Dataset Versioning services..."
    
    try {
        # Build only the dataset-api service
        docker compose -f $COMPOSE_FILE build dataset-api
        Write-Success "✓ Dataset API service built successfully"
        
        # Verify images
        $images = docker images --filter "reference=*dataset*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
        Write-Info "Built images:"
        Write-Output $images
        
    } catch {
        Write-Error "✗ Failed to build services: $_"
        exit 1
    }
}

# Deploy services
function Deploy-Services {
    Write-Info "Deploying Dataset Versioning stack..."
    
    try {
        # Start required dependencies first
        Write-Info "Starting database and cache services..."
        docker compose -f $COMPOSE_FILE up -d mlflow-postgres mlflow-redis
        
        # Wait for database to be ready
        Write-Info "Waiting for database to be ready..."
        $retries = 30
        do {
            Start-Sleep 2
            $dbReady = docker compose -f $COMPOSE_FILE exec -T mlflow-postgres pg_isready -U mlflow -d mlflow
            $retries--
        } while ($LASTEXITCODE -ne 0 -and $retries -gt 0)
        
        if ($retries -eq 0) {
            Write-Error "✗ Database failed to start"
            exit 1
        }
        Write-Success "✓ Database is ready"
        
        # Start dataset API service
        Write-Info "Starting Dataset Versioning API..."
        docker compose -f $COMPOSE_FILE up -d dataset-api
        
        # Wait for API to be ready
        Write-Info "Waiting for API to be ready..."
        $retries = 30
        do {
            Start-Sleep 3
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) { break }
            } catch { }
            $retries--
        } while ($retries -gt 0)
        
        if ($retries -eq 0) {
            Write-Error "✗ Dataset API failed to start"
            Show-ServiceLogs
            exit 1
        }
        Write-Success "✓ Dataset Versioning API is ready"
        
        # Show service status
        Show-ServiceStatus
        
    } catch {
        Write-Error "✗ Failed to deploy services: $_"
        Show-ServiceLogs
        exit 1
    }
}

# Test deployment
function Test-Deployment {
    Write-Info "Testing Dataset Versioning deployment..."
    
    try {
        # Test API health
        Write-Info "Testing API health endpoint..."
        $healthResponse = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method GET
        if ($healthResponse.status -eq "healthy") {
            Write-Success "✓ API health check passed"
        } else {
            Write-Error "✗ API health check failed"
            exit 1
        }
        
        # Test database connection
        Write-Info "Testing database connection..."
        $dbTest = docker compose -f $COMPOSE_FILE exec -T dataset-api python -c "
import asyncio
import asyncpg
async def test_db():
    try:
        conn = await asyncpg.connect('postgresql://mlflow:mlflow_password@mlflow-postgres:5432/mlflow')
        await conn.close()
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
        exit(1)
asyncio.run(test_db())
"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Database connection test passed"
        } else {
            Write-Error "✗ Database connection test failed"
            exit 1
        }
        
        # Test Redis connection
        Write-Info "Testing Redis connection..."
        $redisTest = docker compose -f $COMPOSE_FILE exec -T dataset-api python -c "
import asyncio
import redis.asyncio as redis
async def test_redis():
    try:
        client = redis.from_url('redis://mlflow-redis:6379/3')
        await client.ping()
        await client.close()
        print('Redis connection successful')
    except Exception as e:
        print(f'Redis connection failed: {e}')
        exit(1)
asyncio.run(test_redis())
"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Redis connection test passed"
        } else {
            Write-Error "✗ Redis connection test failed"
            exit 1
        }
        
        # Test API endpoints
        Write-Info "Testing API endpoints..."
        $endpoints = @(
            "/health",
            "/datasets"
        )
        
        foreach ($endpoint in $endpoints) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8080$endpoint" -TimeoutSec 10
                if ($response.StatusCode -eq 200) {
                    Write-Success "✓ Endpoint $endpoint is accessible"
                } else {
                    Write-Warning "⚠ Endpoint $endpoint returned status $($response.StatusCode)"
                }
            } catch {
                Write-Warning "⚠ Endpoint $endpoint is not accessible: $_"
            }
        }
        
        Write-Success "✓ Dataset Versioning deployment tests completed"
        
    } catch {
        Write-Error "✗ Deployment tests failed: $_"
        exit 1
    }
}

# Show service status
function Show-ServiceStatus {
    Write-Info "Service Status:"
    Write-Info "==============="
    
    $services = @("mlflow-postgres", "mlflow-redis", "dataset-api")
    
    foreach ($service in $services) {
        $status = docker compose -f $COMPOSE_FILE ps $service --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        Write-Output $status
    }
    
    Write-Info ""
    Write-Info "Service URLs:"
    Write-Info "=============  "
    Write-Info "Dataset API: http://localhost:8080"
    Write-Info "API Documentation: http://localhost:8080/docs"
    Write-Info "Health Check: http://localhost:8080/health"
    Write-Info "Metrics: http://localhost:8080/metrics"
}

# Show service logs
function Show-ServiceLogs {
    if ($Logs) {
        Write-Info "Recent logs from Dataset Versioning services:"
        Write-Info "============================================="
        docker compose -f $COMPOSE_FILE logs --tail=50 dataset-api
    } else {
        Write-Info "Showing recent error logs..."
        docker compose -f $COMPOSE_FILE logs --tail=20 dataset-api | Select-String -Pattern "ERROR|CRITICAL|Exception"
    }
}

# Stop services
function Stop-Services {
    Write-Info "Stopping Dataset Versioning services..."
    
    try {
        # Stop dataset API first
        docker compose -f $COMPOSE_FILE stop dataset-api
        Write-Success "✓ Dataset API stopped"
        
        # Optionally stop dependencies
        $response = Read-Host "Stop database and Redis services as well? [y/N]"
        if ($response -eq "y" -or $response -eq "Y") {
            docker compose -f $COMPOSE_FILE stop mlflow-postgres mlflow-redis
            Write-Success "✓ All services stopped"
        }
        
    } catch {
        Write-Error "✗ Failed to stop services: $_"
        exit 1
    }
}

# Clean up deployment
function Clean-Deployment {
    Write-Info "Cleaning up Dataset Versioning deployment..."
    
    $response = Read-Host "This will remove containers, volumes, and data. Continue? [y/N]"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Info "Cleanup cancelled"
        return
    }
    
    try {
        # Stop and remove containers
        docker compose -f $COMPOSE_FILE down -v --remove-orphans
        
        # Remove images
        $images = docker images --filter "reference=*dataset*" -q
        if ($images) {
            docker rmi $images -f
        }
        
        # Clean up volumes
        $volumes = @("dataset_cache")
        foreach ($volume in $volumes) {
            docker volume rm "${PWD##*/}_$volume" -f 2>$null
        }
        
        Write-Success "✓ Cleanup completed"
        
    } catch {
        Write-Error "✗ Cleanup failed: $_"
        exit 1
    }
}

# Main execution
try {
    Test-Prerequisites
    Initialize-Directories
    
    if ($Clean) {
        Clean-Deployment
        exit 0
    }
    
    if ($Stop) {
        Stop-Services
        exit 0
    }
    
    if ($Logs) {
        Show-ServiceLogs
        exit 0
    }
    
    if ($Build) {
        Build-Services
    }
    
    if ($Deploy) {
        Deploy-Services
    }
    
    if ($Test) {
        Test-Deployment
    }
    
    if (-not $Build -and -not $Deploy -and -not $Test) {
        Write-Info "No action specified. Available options:"
        Write-Info "  -Build    Build the dataset versioning services"
        Write-Info "  -Deploy   Deploy the dataset versioning stack"
        Write-Info "  -Test     Test the deployment"
        Write-Info "  -Stop     Stop running services"
        Write-Info "  -Logs     Show service logs"
        Write-Info "  -Clean    Clean up deployment"
        Write-Info ""
        Write-Info "Example: .\deploy-dataset-versioning.ps1 -Build -Deploy -Test"
    }
    
} catch {
    Write-Error "Script failed: $_"
    exit 1
}

Write-Success ""
Write-Success "Dataset Versioning deployment script completed successfully!"
Write-Success ""
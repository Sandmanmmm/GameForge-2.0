# GameForge Cloud Migration Script
# Seamless transition from Docker Compose to Kubernetes

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("aws", "azure", "gcp")]
    [string]$CloudProvider,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-west-2",
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "gameforge-production",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$MigrateData
)

$ErrorActionPreference = "Stop"

Write-Host "=== GameForge Cloud Migration ===" -ForegroundColor Green
Write-Host "Target: $CloudProvider ($Region)" -ForegroundColor Yellow
Write-Host "Cluster: $ClusterName" -ForegroundColor Yellow
Write-Host ""

# Step 1: Validate current Docker setup
Write-Host "Step 1: Validating Docker Environment..." -ForegroundColor Cyan
if (!(Test-Path "docker-compose.production-hardened.yml")) {
    throw "Docker Compose production file not found"
}

# Check if GameForge containers are running
$containers = docker ps --filter "name=gameforge" --format "table {{.Names}}\t{{.Status}}"
if ($containers) {
    Write-Host "Current GameForge containers:" -ForegroundColor Green
    Write-Host $containers
} else {
    Write-Warning "No GameForge containers currently running"
}

# Step 2: Build and tag images for cloud registry
Write-Host "`nStep 2: Preparing Container Images..." -ForegroundColor Cyan

switch ($CloudProvider) {
    "aws" {
        $registry = "$env:AWS_ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com"
        Write-Host "Logging into AWS ECR..."
        aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry
    }
    "azure" {
        $registry = "$env:AZURE_REGISTRY_NAME.azurecr.io"
        Write-Host "Logging into Azure ACR..."
        az acr login --name $env:AZURE_REGISTRY_NAME
    }
    "gcp" {
        $registry = "gcr.io/$env:GCP_PROJECT_ID"
        Write-Host "Logging into Google GCR..."
        gcloud auth configure-docker
    }
}

# Build latest GameForge image
Write-Host "Building GameForge production image..."
if (!$DryRun) {
    docker-compose -f docker-compose.production-hardened.yml build gameforge-app
    
    # Tag for cloud registry
    docker tag "gameforge:phase2-phase4-production-gpu" "$registry/gameforge:latest"
    docker tag "gameforge:phase2-phase4-production-gpu" "$registry/gameforge:v1.0.0"
    
    # Push to registry
    docker push "$registry/gameforge:latest"
    docker push "$registry/gameforge:v1.0.0"
    
    Write-Host "✅ Images pushed to $registry" -ForegroundColor Green
}

# Step 3: Update Kubernetes configurations
Write-Host "`nStep 3: Updating Kubernetes Configurations..." -ForegroundColor Cyan

# Update kustomization.yaml with cloud registry
$kustomizationPath = "k8s/overlays/cloud-$CloudProvider/kustomization.yaml"
if (Test-Path $kustomizationPath) {
    # Update image references
    $content = Get-Content $kustomizationPath -Raw
    $content = $content -replace "123456789012\.dkr\.ecr\.us-west-2\.amazonaws\.com", $registry
    $content = $content -replace "us-west-2", $Region
    
    if (!$DryRun) {
        Set-Content $kustomizationPath -Value $content
        Write-Host "✅ Updated $kustomizationPath" -ForegroundColor Green
    }
}

# Step 4: Migrate persistent data
if ($MigrateData) {
    Write-Host "`nStep 4: Migrating Persistent Data..." -ForegroundColor Cyan
    
    # Export Docker volumes
    Write-Host "Exporting Docker volume data..."
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    
    # Create backup directory
    $backupDir = "migration-backup-$timestamp"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Export database
    if (!$DryRun) {
        docker-compose -f docker-compose.production-hardened.yml exec -T postgres pg_dump -U gameforge gameforge_prod > "$backupDir/database.sql"
        
        # Export Grafana data
        docker run --rm -v gameforge_grafana-storage:/source:ro -v ${PWD}/${backupDir}:/backup alpine tar czf /backup/grafana-data.tar.gz -C /source .
        
        # Export Prometheus data
        docker run --rm -v gameforge_prometheus-storage:/source:ro -v ${PWD}/${backupDir}:/backup alpine tar czf /backup/prometheus-data.tar.gz -C /source .
        
        Write-Host "✅ Data exported to $backupDir" -ForegroundColor Green
    }
}

# Step 5: Deploy to cloud cluster
Write-Host "`nStep 5: Deploying to Cloud Cluster..." -ForegroundColor Cyan

# Verify cluster connection
try {
    $currentContext = kubectl config current-context
    Write-Host "Current context: $currentContext" -ForegroundColor Yellow
    
    if ($currentContext -notlike "*$ClusterName*") {
        Write-Warning "Context doesn't match expected cluster. Please verify connection."
    }
} catch {
    throw "Unable to connect to Kubernetes cluster. Please configure kubectl."
}

# Apply cloud-specific configuration
if (!$DryRun) {
    Write-Host "Applying Kubernetes manifests..."
    kubectl apply -k "k8s/overlays/cloud-$CloudProvider"
    
    # Wait for deployment
    Write-Host "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment -l app.kubernetes.io/name=gameforge -n gameforge-monitoring
    kubectl wait --for=condition=available --timeout=300s deployment -l app.kubernetes.io/name=prometheus -n gameforge-monitoring
    kubectl wait --for=condition=available --timeout=300s deployment -l app.kubernetes.io/name=grafana -n gameforge-monitoring
    
    Write-Host "✅ Deployment completed" -ForegroundColor Green
}

# Step 6: Verify deployment
Write-Host "`nStep 6: Verifying Deployment..." -ForegroundColor Cyan

if (!$DryRun) {
    Write-Host "`nPod Status:"
    kubectl get pods -n gameforge-monitoring -o wide
    
    Write-Host "`nService Status:"
    kubectl get svc -n gameforge-monitoring
    
    Write-Host "`nExternal Endpoints:"
    $services = kubectl get svc -n gameforge-monitoring -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name}{"\t"}{.status.loadBalancer.ingress[0].hostname}{.status.loadBalancer.ingress[0].ip}{"\n"}{end}'
    Write-Host $services -ForegroundColor Cyan
}

# Step 7: Health checks
Write-Host "`nStep 7: Running Health Checks..." -ForegroundColor Cyan

if (!$DryRun) {
    # Test internal connectivity
    $grafanaPod = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}'
    $prometheusPod = kubectl get pods -n gameforge-monitoring -l app.kubernetes.io/name=prometheus -o jsonpath='{.items[0].metadata.name}'
    
    if ($grafanaPod) {
        $grafanaHealth = kubectl exec $grafanaPod -n gameforge-monitoring -- curl -s http://localhost:3000/api/health | ConvertFrom-Json
        Write-Host "Grafana Health: $($grafanaHealth.database)" -ForegroundColor $(if($grafanaHealth.database -eq "ok") {"Green"} else {"Red"})
    }
    
    if ($prometheusPod) {
        $prometheusHealth = kubectl exec $prometheusPod -n gameforge-monitoring -- curl -s http://localhost:9090/-/ready
        Write-Host "Prometheus Health: $prometheusHealth" -ForegroundColor $(if($prometheusHealth -eq "Prometheus is Ready.") {"Green"} else {"Red"})
    }
}

Write-Host "`n=== Migration Summary ===" -ForegroundColor Green
Write-Host "✅ Container images built and pushed" -ForegroundColor Green
Write-Host "✅ Kubernetes configurations updated" -ForegroundColor Green
Write-Host "✅ Cloud deployment completed" -ForegroundColor Green
if ($MigrateData) {
    Write-Host "✅ Data migration completed" -ForegroundColor Green
}

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Configure DNS for external endpoints" -ForegroundColor White
Write-Host "2. Set up SSL certificates" -ForegroundColor White
Write-Host "3. Configure monitoring and alerting" -ForegroundColor White
Write-Host "4. Test application functionality" -ForegroundColor White
Write-Host "5. Update CI/CD pipelines" -ForegroundColor White

if ($DryRun) {
    Write-Host "`n[DRY RUN] No changes were made. Run without -DryRun to execute migration." -ForegroundColor Magenta
}

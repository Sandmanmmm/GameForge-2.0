# Advanced Build Caching Script
# Optimizes Docker builds with intelligent cache management

param(
    [string]$Target = "production",
    [string]$Platform = "linux/amd64,linux/arm64", 
    [switch]$ClearCache,
    [switch]$AnalyzeCache,
    [string]$CacheRegistry = "ghcr.io/sandmanmmm/ai-game-production-p"
)

$ErrorActionPreference = "Stop"

function Write-Header($message) {
    Write-Host "`n🔧 $message" -ForegroundColor Green
    Write-Host ("=" * 50)
}

function Get-CacheSize($path) {
    if (Test-Path $path) {
        $size = (Get-ChildItem $path -Recurse -File | Measure-Object -Property Length -Sum).Sum
        return [math]::Round($size / 1MB, 2)
    }
    return 0
}

Write-Header "GameForge Advanced Build Optimization"

# Build configuration
$BuildConfig = @{
    Context = "."
    Dockerfile = "Dockerfile"
    Target = $Target
    Platform = $Platform
    Registry = $CacheRegistry
    CacheDir = ".buildkit-cache"
    BuildKitConfig = ".buildkitd.toml"
}

Write-Host "📊 Configuration:"
$BuildConfig.GetEnumerator() | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value)"
}

# Cache analysis
if ($AnalyzeCache) {
    Write-Header "Cache Analysis"
    
    $cacheSize = Get-CacheSize $BuildConfig.CacheDir
    Write-Host "Local cache size: $cacheSize MB"
    
    # Docker buildx cache analysis
    Write-Host "`n🔍 Docker BuildX cache analysis:"
    docker buildx du --verbose
    
    # Registry cache info
    Write-Host "`n📦 Registry cache info:"
    try {
        docker buildx imagetools inspect "$($BuildConfig.Registry)/buildcache:latest" 2>$null
    } catch {
        Write-Host "No registry cache found"
    }
    
    exit 0
}

# Clear cache if requested
if ($ClearCache) {
    Write-Header "Clearing Build Cache"
    
    docker buildx prune --all --force
    if (Test-Path $BuildConfig.CacheDir) {
        Remove-Item $BuildConfig.CacheDir -Recurse -Force
        Write-Host "✅ Local cache cleared"
    }
    
    Write-Host "✅ Docker BuildX cache cleared"
    exit 0
}

# Setup BuildKit with advanced configuration
Write-Header "Setting up BuildKit"

# Create BuildKit instance with custom config
$builderName = "gameforge-advanced"
$existingBuilder = docker buildx ls | Select-String $builderName

if (-not $existingBuilder) {
    Write-Host "Creating new BuildKit builder: $builderName"
    docker buildx create --name $builderName --driver docker-container --config $BuildConfig.BuildKitConfig
} else {
    Write-Host "Using existing builder: $builderName"
}

docker buildx use $builderName
docker buildx inspect --bootstrap

# Generate optimized cache tags
$cacheFrom = @(
    "type=gha,scope=$Target"
    "type=registry,ref=$($BuildConfig.Registry)/buildcache:$Target"
    "type=local,src=$($BuildConfig.CacheDir)"
)

$cacheTo = @(
    "type=gha,mode=max,scope=$Target"
    "type=registry,ref=$($BuildConfig.Registry)/buildcache:$Target,mode=max"
    "type=local,dest=$($BuildConfig.CacheDir),mode=max"
)

# Pre-build optimizations
Write-Header "Pre-build Optimizations"

# Analyze dependencies for cache efficiency
Write-Host "📦 Analyzing dependencies..."
if (Test-Path "requirements.txt") {
    $pythonDeps = Get-Content "requirements.txt" | Measure-Object -Line
    Write-Host "  Python dependencies: $($pythonDeps.Lines) packages"
}

if (Test-Path "frontend/package.json") {
    $nodePackage = Get-Content "frontend/package.json" | ConvertFrom-Json
    $nodeDeps = ($nodePackage.dependencies.PSObject.Properties).Count
    Write-Host "  Node.js dependencies: $nodeDeps packages"
}

# Generate build metadata
$buildDate = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
try {
    $gitCommit = git rev-parse --short HEAD 2>$null
    if (-not $gitCommit) { $gitCommit = "unknown" }
} catch {
    $gitCommit = "unknown"
}

try {
    $gitBranch = git rev-parse --abbrev-ref HEAD 2>$null
    if (-not $gitBranch) { $gitBranch = "unknown" }
} catch {
    $gitBranch = "unknown"
}

Write-Host "🏷️ Build metadata:"
Write-Host "  Commit: $gitCommit"
Write-Host "  Branch: $gitBranch"
Write-Host "  Date: $buildDate"

# Build with advanced caching
Write-Header "Building with Advanced Caching"

$buildArgs = @(
    "buildx", "build"
    "--target", $Target
    "--platform", $Platform
    "--file", $BuildConfig.Dockerfile
    "--progress", "plain"
    "--metadata-file", "build-metadata.json"
)

# Add cache configurations
foreach ($cache in $cacheFrom) {
    $buildArgs += "--cache-from", $cache
}

foreach ($cache in $cacheTo) {
    $buildArgs += "--cache-to", $cache
}

# Add build arguments
$buildArgs += @(
    "--build-arg", "BUILDKIT_INLINE_CACHE=1"
    "--build-arg", "BUILD_DATE=$buildDate"
    "--build-arg", "VCS_REF=$gitCommit"
    "--build-arg", "VERSION=$gitBranch-$gitCommit"
)

# Add labels
$buildArgs += @(
    "--label", "org.opencontainers.image.created=$buildDate"
    "--label", "org.opencontainers.image.revision=$gitCommit"
    "--label", "org.opencontainers.image.source=https://github.com/Sandmanmmm/ai-game-production-p"
)

# Execute build
$buildArgs += "."

Write-Host "🚀 Executing build command:"
Write-Host "docker $($buildArgs -join ' ')" -ForegroundColor Yellow

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
& docker @buildArgs

if ($LASTEXITCODE -eq 0) {
    $stopwatch.Stop()
    Write-Header "Build Complete!"
    Write-Host "✅ Build succeeded in $($stopwatch.Elapsed.TotalMinutes.ToString('F2')) minutes"
    
    # Post-build cache analysis
    $newCacheSize = Get-CacheSize $BuildConfig.CacheDir
    Write-Host "📊 Local cache size after build: $newCacheSize MB"
    
    # Display build metadata
    if (Test-Path "build-metadata.json") {
        $metadata = Get-Content "build-metadata.json" | ConvertFrom-Json
        Write-Host "🏷️ Built image digest: $($metadata.containerimage.digest)"
    }
    
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Header "Cache Management Recommendations"
Write-Host "💡 To optimize future builds:"
Write-Host "  • Use --cache-from for faster rebuilds"
Write-Host "  • Consider layer ordering in Dockerfile"
Write-Host "  • Use .dockerignore to exclude unnecessary files"
Write-Host "  • Leverage multi-stage builds for smaller images"

if ($newCacheSize -gt 1000) {
    Write-Host "⚠️ Cache size is large ($newCacheSize MB). Consider periodic cleanup."
}
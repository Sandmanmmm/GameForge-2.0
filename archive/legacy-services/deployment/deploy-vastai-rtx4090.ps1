# PowerShell script for Windows deployment to Vast.ai RTX4090
# GameForge Enhanced Generation Engine

param(
    [switch]$Build,
    [switch]$Deploy,
    [switch]$Monitor,
    [string]$InstanceId = ""
)

# Configuration
$ProjectName = "gameforge-enhanced-generation"
$DockerImage = "gameforge/enhanced-gen:rtx4090"
$VastInstanceType = "rtx4090"
$MinGpuMemory = "20000"  # 20GB minimum
$MinRam = "28000"        # 28GB minimum  
$MinDisk = "80"          # 80GB minimum

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Write-LogInfo($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-LogSuccess($Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-LogWarning($Message) {
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-LogError($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

function Test-Prerequisites {
    Write-LogInfo "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-LogSuccess "Python found: $pythonVersion"
    }
    catch {
        Write-LogError "Python not found. Please install Python 3.10+"
        return $false
    }
    
    # Check pip
    try {
        pip --version | Out-Null
        Write-LogSuccess "pip found"
    }
    catch {
        Write-LogError "pip not found"
        return $false
    }
    
    # Check/Install vastai
    try {
        vast --help | Out-Null
        Write-LogSuccess "vastai CLI found"
    }
    catch {
        Write-LogWarning "vastai CLI not found. Installing..."
        pip install vastai
    }
    
    return $true
}

function Install-Dependencies {
    Write-LogInfo "Installing Python dependencies for local testing..."
    
    # Install core dependencies that don't require GPU
    $coreDependencies = @(
        "torch --index-url https://download.pytorch.org/whl/cpu",
        "torchvision --index-url https://download.pytorch.org/whl/cpu",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "redis>=5.0.1",
        "aioredis>=2.0.1",
        "opencv-python>=4.8.0",
        "soundfile>=0.12.1",
        "tqdm>=4.66.0",
        "rich>=13.7.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.25.0",
        "aiofiles>=23.2.1"
    )
    
    foreach ($dep in $coreDependencies) {
        Write-LogInfo "Installing: $dep"
        pip install $dep.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
        if ($LASTEXITCODE -ne 0) {
            Write-LogWarning "Failed to install $dep - continuing..."
        }
    }
    
    Write-LogSuccess "Core dependencies installed"
}

function Build-LocalDockerfile {
    Write-LogInfo "Creating optimized Dockerfile for RTX4090..."
    
    $dockerfileContent = @"
# GameForge Enhanced Generation Engine - RTX4090 Optimized
FROM nvidia/cuda:12.1-cudnn8-devel-ubuntu22.04

# Set environment variables for RTX4090 optimization
ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=`${CUDA_HOME}/bin:`${PATH}
ENV LD_LIBRARY_PATH=`${CUDA_HOME}/lib64:`${LD_LIBRARY_PATH}
ENV TORCH_CUDA_ARCH_LIST="8.9"
ENV FORCE_CUDA="1"
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV TOKENIZERS_PARALLELISM=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    curl \
    unzip \
    build-essential \
    cmake \
    ninja-build \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    htop \
    nvidia-smi \
    && rm -rf /var/lib/apt/lists/*

# Create python symlink
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install PyTorch with CUDA 12.1 for RTX4090
RUN pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu121

# Install xFormers for memory optimization
RUN pip install xformers==0.0.22.post7 --index-url https://download.pytorch.org/whl/cu121

# Install diffusion models and ML libraries
RUN pip install diffusers==0.24.0 transformers==4.35.0 accelerate==0.24.0

# Install image and audio processing
RUN pip install Pillow==10.0.0 opencv-python==4.8.0.76 soundfile==0.12.1

# Install web framework
RUN pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0

# Install Redis and utilities
RUN pip install redis==5.0.1 aioredis==2.0.1 numpy==1.24.4

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/generated_assets /app/asset_cache /app/models /app/logs
RUN chmod -R 755 /app

# Copy application code
COPY . /app/

# Install requirements if available
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5m --retries=3 \
    CMD python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" || exit 1

# Expose port
EXPOSE 8080

# Default command
CMD ["python", "-m", "services.asset-gen-v2.main"]
"@

    $dockerfileContent | Out-File -FilePath "Dockerfile.vastai-rtx4090" -Encoding UTF8
    Write-LogSuccess "Dockerfile created: Dockerfile.vastai-rtx4090"
}

function Start-LocalTest {
    Write-LogInfo "Starting local test of Enhanced Generation Engine..."
    
    # Create test script
    $testScript = @"
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

from services.asset_gen_v2.enhanced_generation_engine import create_enhanced_engine, GenerationRequest, AssetType, QualityTier

async def test_engine():
    print("🧪 Testing Enhanced Generation Engine...")
    
    # Create engine
    config = {
        "output_dir": "./test_output",
        "cache_dir": "./test_cache",
        "max_workers": 2
    }
    
    engine = create_enhanced_engine(config)
    
    # Health check
    health = await engine.health_check()
    print(f"📊 Health Status: {health}")
    
    # Test texture generation
    request = GenerationRequest(
        asset_type=AssetType.TEXTURE_2D,
        prompt="stone brick wall texture",
        quality_tier=QualityTier.PC,
        batch_size=2
    )
    
    print(f"🎨 Generating textures...")
    assets = await engine.generate_asset(request)
    
    print(f"✅ Generated {len(assets)} assets:")
    for asset in assets:
        print(f"  - {asset.asset_id}: {asset.file_path}")
        print(f"    Quality: {asset.quality_metrics.get('overall', 0):.2f}")
    
    # Get stats
    stats = await engine.get_generation_stats()
    print(f"📈 Generation Stats: {stats}")
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_engine())
        print("🎉 Test completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
"@

    $testScript | Out-File -FilePath "test_enhanced_engine_local.py" -Encoding UTF8
    
    # Run test
    python test_enhanced_engine_local.py
}

function Find-VastAiInstance {
    Write-LogInfo "Searching for RTX4090 instances on vast.ai..."
    
    # Search for instances
    $searchResult = vast search offers --type=bid --gpu_name="RTX_4090" --gpu_ram=$MinGpuMemory --ram=$MinRam --disk=$MinDisk --sort_by="score" --order=desc --limit=10 --format=json
    
    if ($searchResult) {
        $searchResult | Out-File -FilePath "available_instances.json" -Encoding UTF8
        Write-LogSuccess "Found RTX4090 instances"
        
        # Parse and display options
        $instances = $searchResult | ConvertFrom-Json
        if ($instances.Count -gt 0) {
            Write-LogInfo "Top available instances:"
            for ($i = 0; $i -lt [Math]::Min(3, $instances.Count); $i++) {
                $instance = $instances[$i]
                Write-Host "  $($i+1). ID: $($instance.id) | GPU: $($instance.gpu_name) | RAM: $($instance.ram)GB | Price: `$$($instance.dph_total)/hr"
            }
            
            return $instances[0].id
        }
    }
    
    Write-LogError "No suitable RTX4090 instances found"
    return $null
}

function Deploy-ToVastAi {
    param([string]$InstanceId)
    
    Write-LogInfo "Deploying to vast.ai instance: $InstanceId"
    
    # Create instance
    $createResult = vast create instance $InstanceId --image $DockerImage --disk $MinDisk --onstart-cmd "cd /app && python -m services.asset-gen-v2.main" --ssh
    
    if ($createResult -match "Started\. New instance is (\d+)") {
        $newInstanceId = $Matches[1]
        Write-LogSuccess "Instance created: $newInstanceId"
        
        # Save instance ID
        $newInstanceId | Out-File -FilePath "vast_instance_id.txt" -Encoding UTF8
        
        # Wait for instance to be ready
        Write-LogInfo "Waiting for instance to be ready..."
        Start-Sleep 30
        
        return $newInstanceId
    }
    
    Write-LogError "Failed to create instance"
    return $null
}

function Monitor-Instance {
    param([string]$InstanceId)
    
    Write-LogInfo "Monitoring instance: $InstanceId"
    
    # Get instance status
    $status = vast show instance $InstanceId --format=json
    
    if ($status) {
        $instanceInfo = $status | ConvertFrom-Json
        
        Write-LogInfo "Instance Status:"
        Write-Host "  Status: $($instanceInfo[0].actual_status)"
        Write-Host "  SSH: $($instanceInfo[0].ssh_host):$($instanceInfo[0].ssh_port)"
        Write-Host "  Public IP: $($instanceInfo[0].public_ipaddr)"
        
        # Check if API is accessible
        if ($instanceInfo[0].public_ipaddr) {
            $apiUrl = "http://$($instanceInfo[0].public_ipaddr):8080/health"
            Write-LogInfo "Testing API endpoint: $apiUrl"
            
            try {
                $response = Invoke-WebRequest -Uri $apiUrl -TimeoutSec 10
                Write-LogSuccess "API is responding: $($response.StatusCode)"
            }
            catch {
                Write-LogWarning "API not yet accessible: $($_.Exception.Message)"
            }
        }
    }
}

function Show-Usage {
    Write-Host @"
GameForge Enhanced Generation Engine - Vast.ai Deployment

Usage:
  .\deploy-vastai-rtx4090.ps1 [options]

Options:
  -Build         Build Docker image and run local tests
  -Deploy        Deploy to vast.ai RTX4090 instance
  -Monitor       Monitor existing instance
  -InstanceId    Specify instance ID for monitoring

Examples:
  .\deploy-vastai-rtx4090.ps1 -Build
  .\deploy-vastai-rtx4090.ps1 -Deploy
  .\deploy-vastai-rtx4090.ps1 -Monitor -InstanceId "12345"

"@
}

# Main execution
function Main {
    Write-LogInfo "🚀 GameForge Enhanced Generation Engine - Vast.ai Deployment"
    
    if (-not $Build -and -not $Deploy -and -not $Monitor) {
        Show-Usage
        return
    }
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-LogError "Prerequisites not met"
        return
    }
    
    if ($Build) {
        Install-Dependencies
        Build-LocalDockerfile
        Start-LocalTest
    }
    
    if ($Deploy) {
        $selectedInstanceId = Find-VastAiInstance
        if ($selectedInstanceId) {
            $deployedInstanceId = Deploy-ToVastAi -InstanceId $selectedInstanceId
            if ($deployedInstanceId) {
                Monitor-Instance -InstanceId $deployedInstanceId
            }
        }
    }
    
    if ($Monitor -and $InstanceId) {
        Monitor-Instance -InstanceId $InstanceId
    }
    elseif ($Monitor -and (Test-Path "vast_instance_id.txt")) {
        $storedInstanceId = Get-Content "vast_instance_id.txt"
        Monitor-Instance -InstanceId $storedInstanceId
    }
    elseif ($Monitor) {
        Write-LogError "No instance ID provided or found"
    }
}

# Run main function
Main

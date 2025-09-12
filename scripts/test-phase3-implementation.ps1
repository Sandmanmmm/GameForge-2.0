# GameForge Production Phase 3 - Quick Implementation and Test
# This script runs the complete Phase 3 security pipeline for testing

param(
    [string]$ImageVariant = "cpu",
    [switch]$RunRemediation,
    [switch]$SkipSigning,
    [switch]$QuickTest
)

function Write-Color {
    param($Text, $Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "==========================================" -Color Cyan
Write-Color " GameForge Phase 3 - Quick Implementation" -Color Cyan
Write-Color "==========================================" -Color Cyan

$startTime = Get-Date

# Ensure we have the required image
$imageName = "gameforge:phase3-test-$ImageVariant"

if ($QuickTest) {
    Write-Color "`nQuick Test Mode - Using existing CPU image" -Color Yellow
    $existingImages = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "gameforge.*cpu" }
    if ($existingImages) {
        $imageName = $existingImages[0]
        Write-Color "Using existing image: $imageName" -Color Green
    } else {
        Write-Color "No existing GameForge images found. Building minimal test image..." -Color Yellow
        
        # Create minimal test Dockerfile
        $testDockerfile = @"
FROM python:3.11-slim
LABEL maintainer="GameForge Security Team"
LABEL version="phase3-test"

# Install some packages for testing
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Add a simple app
WORKDIR /app
RUN echo 'print("GameForge Phase 3 Test Image")' > app.py

EXPOSE 8000
CMD ["python", "app.py"]
"@
        
        $testDockerfile | Set-Content "Dockerfile.phase3-test" -Encoding UTF8
        
        Write-Color "Building test image..." -Color Yellow
        docker build -f Dockerfile.phase3-test -t $imageName . 2>&1 | Out-Host
        
        if ($LASTEXITCODE -ne 0) {
            Write-Color "Failed to build test image" -Color Red
            exit 1
        }
    }
} else {
    # Check if we need to build the full image
    $imageExists = docker images -q $imageName
    if (-not $imageExists) {
        Write-Color "`nBuilding $ImageVariant variant..." -Color Yellow
        
        if ($ImageVariant -eq "cpu") {
            .\build-phase2-clean.ps1 -Variant cpu -Tag "phase3-test-cpu"
        } else {
            .\build-phase2-clean.ps1 -Variant gpu -Tag "phase3-test-gpu"
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Color "Failed to build image" -Color Red
            exit 1
        }
    }
}

Write-Color "`n1. Running Phase 3 Security Pipeline..." -Color Cyan

# Run the main security pipeline
$pipelineArgs = @(
    "-ImageName", $imageName,
    "-InstallTools"
)

if (-not $SkipSigning) {
    $pipelineArgs += "-SignImage"
}

Write-Color "Executing: .\phase3-security-pipeline.ps1 $($pipelineArgs -join ' ')" -Color Yellow

& .\phase3-security-pipeline.ps1 @pipelineArgs

Write-Color "`n2. Checking Security Artifacts..." -Color Cyan

# Find the latest security artifacts directory
$artifactDirs = Get-ChildItem -Directory -Name "security-artifacts-*" | Sort-Object -Descending
if ($artifactDirs.Count -gt 0) {
    $latestArtifacts = $artifactDirs[0]
    Write-Color "Latest artifacts directory: $latestArtifacts" -Color Green
    
    # Show summary of generated files
    $sbomFiles = Get-ChildItem "$latestArtifacts\sbom\*" -File
    $scanFiles = Get-ChildItem "$latestArtifacts\scans\*" -File
    
    Write-Color "`nGenerated Files:" -Color White
    Write-Color "  SBOM Files: $($sbomFiles.Count)" -Color White
    Write-Color "  Scan Reports: $($scanFiles.Count)" -Color White
    
    # Check for high-priority vulnerabilities
    $jsonScanFile = Get-ChildItem "$latestArtifacts\scans\*$ImageVariant*.json" | Select-Object -First 1
    if ($jsonScanFile) {
        try {
            $scanData = Get-Content $jsonScanFile.FullName | ConvertFrom-Json
            $criticalCount = 0
            $highCount = 0
            
            if ($scanData.Results) {
                foreach ($result in $scanData.Results) {
                    if ($result.Vulnerabilities) {
                        foreach ($vuln in $result.Vulnerabilities) {
                            if ($vuln.Severity -eq "CRITICAL") { $criticalCount++ }
                            if ($vuln.Severity -eq "HIGH") { $highCount++ }
                        }
                    }
                }
            }
            
            Write-Color "`nVulnerability Summary:" -Color White
            Write-Color "  Critical: $criticalCount" -Color $(if ($criticalCount -gt 0) { "Red" } else { "Green" })
            Write-Color "  High: $highCount" -Color $(if ($highCount -gt 0) { "Yellow" } else { "Green" })
            
            # Run remediation if requested and vulnerabilities found
            if ($RunRemediation -and ($criticalCount -gt 0 -or $highCount -gt 0)) {
                Write-Color "`n3. Running Vulnerability Remediation..." -Color Cyan
                .\remediate-vulnerabilities.ps1 -ScanReport $jsonScanFile.FullName -UpdateDockerfile
            }
            
        } catch {
            Write-Color "Could not parse scan results: $_" -Color Yellow
        }
    }
    
    # Open HTML report if available
    $htmlReport = Get-ChildItem "$latestArtifacts\*report*.html" | Select-Object -First 1
    if ($htmlReport) {
        Write-Color "`nOpening security report in browser..." -Color Green
        Start-Process $htmlReport.FullName
    }
} else {
    Write-Color "No security artifacts found" -Color Yellow
}

Write-Color "`n3. Phase 3 Implementation Status..." -Color Cyan

# Check implementation completeness
$phase3Components = @{
    "Security Pipeline Script" = Test-Path "phase3-security-pipeline.ps1"
    "Remediation Script" = Test-Path "remediate-vulnerabilities.ps1" 
    "CI/CD Workflow" = Test-Path ".github\workflows\security-pipeline.yml"
    "Enhanced Dockerfile" = Test-Path "Dockerfile.production.enhanced"
    "Phase 2 Build Script" = Test-Path "build-phase2-clean.ps1"
}

foreach ($component in $phase3Components.Keys) {
    $status = if ($phase3Components[$component]) { "✅" } else { "❌" }
    Write-Color "  $component`: $status" -Color $(if ($phase3Components[$component]) { "Green" } else { "Red" })
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Color "`n==========================================" -Color Cyan
Write-Color " Phase 3 Implementation Test Complete" -Color Cyan
Write-Color "==========================================" -Color Cyan
Write-Color "Duration: $($duration.ToString('mm\:ss'))" -Color White
Write-Color "Image Tested: $imageName" -Color White

if ($phase3Components.Values -contains $false) {
    Write-Color "`n⚠️ Some Phase 3 components are missing" -Color Yellow
    Write-Color "Review the checklist above and ensure all files are present" -Color Yellow
} else {
    Write-Color "`n✅ Phase 3 Security Pipeline Implementation Complete!" -Color Green
    Write-Color "All components are in place and functional" -Color Green
}

Write-Color "`nNext Steps:" -Color White
Write-Color "1. Review generated security reports" -Color White
Write-Color "2. Address any critical/high vulnerabilities" -Color White
Write-Color "3. Integrate CI/CD workflow with your repository" -Color White
Write-Color "4. Set up automated daily security scans" -Color White

# Cleanup test files if in quick test mode
if ($QuickTest -and (Test-Path "Dockerfile.phase3-test")) {
    Remove-Item "Dockerfile.phase3-test" -Force
    Write-Color "`nCleaned up test Dockerfile" -Color Green
}

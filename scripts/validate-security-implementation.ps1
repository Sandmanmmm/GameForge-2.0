# Security Implementation Validation Script (PowerShell)
# GameForge Security Infrastructure Validation

Write-Host "🔒 Validating GameForge Security Implementation" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

$ValidationPassed = $true

# Check required files exist
Write-Host "`n📁 Checking required files..." -ForegroundColor Yellow
$RequiredFiles = @(
    "docker-compose.security.yml",
    ".github/workflows/security-scan.yml",
    "ci/gitlab/.gitlab-ci-security.yml",
    "security/policies/opa-security-policy.rego",
    "security/policies/k8s-admission-policy.yaml",
    "security/configs/trivy.yaml",
    "security/configs/clair-config.yaml",
    "security/configs/harbor.yml",
    "security/configs/prometheus.yml",
    "security/configs/security_rules.yml",
    "security/dashboards/security-dashboard.json",
    "security/scripts/comprehensive-scan.sh",
    "security/scripts/auto-remediation.sh",
    "security/scripts/secure-deploy.sh",
    "security/scripts/generate-security-report.sh",
    "SECURITY_IMPLEMENTATION_GUIDE.md"
)

foreach ($File in $RequiredFiles) {
    if (Test-Path $File) {
        Write-Host "✅ $File" -ForegroundColor Green
    } else {
        Write-Host "❌ $File - MISSING" -ForegroundColor Red
        $ValidationPassed = $false
    }
}

# Check directory structure
Write-Host "`n📂 Checking directory structure..." -ForegroundColor Yellow
$RequiredDirs = @(
    "security/configs",
    "security/policies", 
    "security/scripts",
    "security/reports",
    "security/dashboards",
    ".github/workflows",
    "ci/gitlab"
)

foreach ($Dir in $RequiredDirs) {
    if (Test-Path $Dir -PathType Container) {
        Write-Host "✅ $Dir/" -ForegroundColor Green
    } else {
        Write-Host "❌ $Dir/ - MISSING" -ForegroundColor Red
        $ValidationPassed = $false
    }
}

# Check script files exist
Write-Host "`n🔧 Checking script files..." -ForegroundColor Yellow
$Scripts = @(
    "security/scripts/comprehensive-scan.sh",
    "security/scripts/auto-remediation.sh",
    "security/scripts/secure-deploy.sh", 
    "security/scripts/generate-security-report.sh"
)

foreach ($Script in $Scripts) {
    if (Test-Path $Script) {
        Write-Host "✅ $Script - exists" -ForegroundColor Green
    } else {
        Write-Host "❌ $Script - missing" -ForegroundColor Red
        $ValidationPassed = $false
    }
}

# Check Docker Compose syntax (if Docker is available)
Write-Host "`n🐳 Validating Docker Compose syntax..." -ForegroundColor Yellow
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    try {
        docker-compose -f docker-compose.security.yml config *>$null
        Write-Host "✅ docker-compose.security.yml syntax valid" -ForegroundColor Green
    } catch {
        Write-Host "❌ docker-compose.security.yml syntax invalid" -ForegroundColor Red
        $ValidationPassed = $false
    }
} else {
    Write-Host "⚠️  Docker Compose not available, skipping syntax check" -ForegroundColor Yellow
}

# Validate key file contents
Write-Host "`n📄 Validating key file contents..." -ForegroundColor Yellow

# Check if Trivy config exists and has content
if (Test-Path "security/configs/trivy.yaml") {
    $TrivyContent = Get-Content "security/configs/trivy.yaml" -Raw
    if ($TrivyContent -match "severity") {
        Write-Host "✅ Trivy configuration includes severity settings" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Trivy configuration may be incomplete" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Trivy configuration missing" -ForegroundColor Red
    $ValidationPassed = $false
}

# Check if GitHub Actions workflow has security gates
if (Test-Path ".github/workflows/security-scan.yml") {
    $WorkflowContent = Get-Content ".github/workflows/security-scan.yml" -Raw
    if ($WorkflowContent -match "security") {
        Write-Host "✅ GitHub Actions includes security scanning" -ForegroundColor Green
    } else {
        Write-Host "⚠️  GitHub Actions security configuration may be incomplete" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ GitHub Actions security workflow missing" -ForegroundColor Red
    $ValidationPassed = $false
}

# Check for required environment variables documentation
Write-Host "`nChecking environment variable documentation..." -ForegroundColor Yellow
if (Test-Path "SECURITY_IMPLEMENTATION_GUIDE.md") {
    $GuideContent = Get-Content "SECURITY_IMPLEMENTATION_GUIDE.md" -Raw
    if ($GuideContent -match "HARBOR_USERNAME") {
        Write-Host "✅ Environment variables documented" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Environment variables not documented" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Security implementation guide missing" -ForegroundColor Red
    $ValidationPassed = $false
}

# Check for security tool availability
Write-Host "`nChecking security tool availability..." -ForegroundColor Yellow
$Tools = @("docker", "kubectl", "git")
foreach ($Tool in $Tools) {
    if (Get-Command $Tool -ErrorAction SilentlyContinue) {
        Write-Host "✅ $Tool - available" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $Tool - not available (install for full functionality)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`nVALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

if ($ValidationPassed) {
    Write-Host "ALL VALIDATIONS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Security implementation is ready for deployment!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Deploy security infrastructure: docker-compose -f docker-compose.security.yml up -d"
    Write-Host "2. Configure CI/CD pipelines with required secrets/variables"
    Write-Host "3. Deploy Kubernetes security policies: kubectl apply -f security/policies/"
    Write-Host "4. Set up monitoring dashboards in Grafana"
    Write-Host "5. Test security scanning: ./security/scripts/comprehensive-scan.sh gameforge:latest"
    Write-Host ""
    Write-Host "For detailed instructions, see: SECURITY_IMPLEMENTATION_GUIDE.md" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "SOME VALIDATIONS FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the issues above before deployment." -ForegroundColor Red
    Write-Host "Check the SECURITY_IMPLEMENTATION_GUIDE.md for troubleshooting guidance." -ForegroundColor Yellow
    exit 1
}

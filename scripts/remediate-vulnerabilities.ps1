# Vulnerability Remediation Script for GameForge Production Phase 3
# This script analyzes trivy scan results and provides automated remediation guidance
param(
    [Parameter(Mandatory = $true)]
    [string]$ScanReport,
    
    [switch]$AutoFix,
    [switch]$UpdateDockerfile,
    [string]$DockerfilePath = "Dockerfile.production.enhanced"
)

function Write-Color {
    param($Text, $Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "====================================" -Color Cyan
Write-Color " GameForge Vulnerability Remediation" -Color Cyan
Write-Color "====================================" -Color Cyan

if (-not (Test-Path $ScanReport)) {
    Write-Color "Error: Scan report not found: $ScanReport" -Color Red
    exit 1
}

try {
    $scanData = Get-Content $ScanReport | ConvertFrom-Json
} catch {
    Write-Color "Error: Unable to parse scan report: $_" -Color Red
    exit 1
}

$remediationActions = @()
$packageUpdates = @{}

Write-Color "`nAnalyzing vulnerabilities..." -Color Yellow

if ($scanData.Results) {
    foreach ($result in $scanData.Results) {
        if ($result.Vulnerabilities) {
            Write-Color "`nTarget: $($result.Target)" -Color White
            
            foreach ($vuln in $result.Vulnerabilities) {
                if ($vuln.Severity -in @("CRITICAL", "HIGH")) {
                    $action = @{
                        Package = $vuln.PkgName
                        CurrentVersion = $vuln.InstalledVersion
                        Severity = $vuln.Severity
                        VulnID = $vuln.VulnerabilityID
                        Title = $vuln.Title
                        FixedVersion = $vuln.FixedVersion
                        Target = $result.Target
                    }
                    
                    $remediationActions += $action
                    
                    # Group package updates
                    if ($vuln.FixedVersion -and $vuln.FixedVersion -ne "") {
                        $packageUpdates[$vuln.PkgName] = @{
                            Current = $vuln.InstalledVersion
                            Fixed = $vuln.FixedVersion
                            Severity = $vuln.Severity
                        }
                    }
                    
                    Write-Color "  🔴 $($vuln.Severity): $($vuln.PkgName) $($vuln.InstalledVersion)" -Color Red
                    if ($vuln.FixedVersion) {
                        Write-Color "     Fix available: $($vuln.FixedVersion)" -Color Green
                    } else {
                        Write-Color "     No fix available yet" -Color Yellow
                    }
                }
            }
        }
    }
}

Write-Color "`n===== REMEDIATION SUMMARY =====" -Color Cyan
Write-Color "Total Critical/High vulnerabilities: $($remediationActions.Count)" -Color White

if ($packageUpdates.Count -gt 0) {
    Write-Color "`nPackages requiring updates:" -Color Yellow
    foreach ($pkg in $packageUpdates.Keys) {
        $update = $packageUpdates[$pkg]
        Write-Color "  ${pkg}: $($update.Current) → $($update.Fixed) [$($update.Severity)]" -Color White
    }
}

# Generate Dockerfile recommendations
if ($UpdateDockerfile -and (Test-Path $DockerfilePath)) {
    Write-Color "`nGenerating Dockerfile updates..." -Color Yellow
    
    $dockerfileContent = Get-Content $DockerfilePath
    $newDockerfileContent = @()
    $inSystemPackagesSection = $false
    
    foreach ($line in $dockerfileContent) {
        if ($line -match "apt-get install.*-y") {
            $inSystemPackagesSection = $true
        }
        
        if ($inSystemPackagesSection -and $line.Trim() -eq "") {
            $inSystemPackagesSection = $false
        }
        
        # Add security-focused package versions
        if ($line -match "apt-get install" -and $packageUpdates.Count -gt 0) {
            $newDockerfileContent += $line
            $newDockerfileContent += "# Security: Pin vulnerable packages to fixed versions"
            foreach ($pkg in $packageUpdates.Keys) {
                $update = $packageUpdates[$pkg]
                if ($update.Severity -eq "CRITICAL") {
                    $newDockerfileContent += "# CRITICAL: $pkg=$($update.Fixed)"
                }
            }
        } else {
            $newDockerfileContent += $line
        }
    }
    
    # Backup original
    $backupPath = "$DockerfilePath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $DockerfilePath $backupPath
    Write-Color "Backed up original to: $backupPath" -Color Green
    
    # Write updated Dockerfile
    $newDockerfileContent | Set-Content "$DockerfilePath.remediated"
    Write-Color "Updated Dockerfile saved as: $DockerfilePath.remediated" -Color Green
}

# Generate remediation commands
$remediationScript = @"
#!/bin/bash
# Auto-generated remediation commands for GameForge
# Generated: $(Get-Date)

echo "Starting vulnerability remediation..."

"@

if ($packageUpdates.Count -gt 0) {
    $remediationScript += @"

# Update system packages
apt-get update

"@
    
    foreach ($pkg in $packageUpdates.Keys) {
        $update = $packageUpdates[$pkg]
        if ($update.Fixed -ne "" -and $update.Severity -eq "CRITICAL") {
            $remediationScript += "apt-get install -y $pkg=$($update.Fixed)`n"
        }
    }
}

$remediationScript += @"

# Clean up
apt-get autoremove -y
apt-get autoclean
rm -rf /var/lib/apt/lists/*

echo "Remediation complete!"
"@

# Save remediation script
$scriptPath = "remediation-$(Get-Date -Format 'yyyyMMdd-HHmmss').sh"
$remediationScript | Set-Content $scriptPath -Encoding UTF8
Write-Color "`nRemediation script saved: $scriptPath" -Color Green

# Generate security report
$reportPath = "remediation-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
$report = @"
# GameForge Vulnerability Remediation Report
Generated: $(Get-Date)

## Summary
- Total vulnerabilities analyzed: $($remediationActions.Count)
- Critical vulnerabilities: $(($remediationActions | Where-Object { $_.Severity -eq "CRITICAL" }).Count)
- High vulnerabilities: $(($remediationActions | Where-Object { $_.Severity -eq "HIGH" }).Count)
- Packages with fixes available: $($packageUpdates.Count)

## Recommended Actions

### 1. Base Image Updates
Consider updating to a newer base image version:
- Current: Review your base image in $DockerfilePath
- Recommendation: Use latest LTS versions with security patches

### 2. Package Updates
"@

foreach ($pkg in $packageUpdates.Keys) {
    $update = $packageUpdates[$pkg]
    $report += "`n- **$pkg**: $($update.Current) → $($update.Fixed) ($($update.Severity))"
}

$report += @"

### 3. Dockerfile Hardening
- Pin all package versions to specific, patched versions
- Use multi-stage builds to minimize attack surface
- Run containers as non-root user
- Remove unnecessary packages and files

### 4. Container Runtime Security
- Use security contexts and capabilities dropping
- Implement resource limits
- Use read-only filesystems where possible
- Enable container scanning in CI/CD pipeline

## Next Steps
1. Review and test the generated remediation script: `$scriptPath`
2. Update your Dockerfile with pinned package versions
3. Rebuild and rescan your images
4. Implement automated vulnerability scanning in your CI/CD pipeline

## Files Generated
- Remediation script: `$scriptPath`
- Updated Dockerfile: `$DockerfilePath.remediated` (if requested)
- This report: `$reportPath`
"@

$report | Set-Content $reportPath -Encoding UTF8
Write-Color "Remediation report saved: $reportPath" -Color Green

# Auto-fix option
if ($AutoFix) {
    Write-Color "`nApplying automatic fixes..." -Color Yellow
    
    if ($IsWindows) {
        Write-Color "Auto-fix requires Linux environment for package updates" -Color Yellow
        Write-Color "Use the generated script: $scriptPath in your Docker build" -Color Yellow
    } else {
        Write-Color "Executing remediation script..." -Color Yellow
        chmod +x $scriptPath
        & ./$scriptPath
    }
}

Write-Color "`n✅ Vulnerability remediation analysis complete!" -Color Green
Write-Color "Review the generated files and apply the recommended fixes." -Color White

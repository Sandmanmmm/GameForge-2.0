# GPU Node Preparation and Labeling Script
# Prepares and labels GPU nodes for AI workload scheduling

param(
    [string]$Action = "setup",
    [string[]]$NodeNames = @(),
    [string]$GPUType = "nvidia-tesla",
    [string]$MemoryTier = "high",
    [string]$WorkloadType = "mixed",
    [switch]$AutoDetect = $false,
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

if ($Verbose) {
    $VerbosePreference = "Continue"
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Get-GPUNodes {
    Write-Log "Detecting GPU nodes..." -Level "INFO"
    
    try {
        # Get all nodes
        $allNodes = kubectl get nodes -o json | ConvertFrom-Json
        $gpuNodes = @()
        
        foreach ($node in $allNodes.items) {
            $nodeName = $node.metadata.name
            $nodeInfo = kubectl describe node $nodeName 2>$null
            
            # Look for NVIDIA GPU indicators
            if ($nodeInfo -match "nvidia\.com/gpu" -or $nodeInfo -match "NVIDIA" -or $nodeInfo -match "GeForce" -or $nodeInfo -match "Tesla" -or $nodeInfo -match "RTX") {
                Write-Log "Found GPU node: $nodeName" -Level "SUCCESS"
                $gpuNodes += $nodeName
            }
        }
        
        if ($gpuNodes.Count -eq 0) {
            Write-Log "No GPU nodes detected automatically" -Level "WARN"
            Write-Log "You may need to specify node names manually" -Level "WARN"
        } else {
            Write-Log "Detected $($gpuNodes.Count) GPU nodes" -Level "SUCCESS"
        }
        
        return $gpuNodes
    }
    catch {
        Write-Log "Failed to detect GPU nodes: $_" -Level "ERROR"
        return @()
    }
}

function Get-NodeGPUInfo {
    param([string]$NodeName)
    
    try {
        $nodeInfo = kubectl describe node $NodeName 2>$null
        $gpuInfo = @{
            HasGPU = $false
            GPUCount = 0
            GPUType = "unknown"
            MemoryGB = 0
        }
        
        # Parse GPU information
        if ($nodeInfo -match "nvidia\.com/gpu:\s+(\d+)") {
            $gpuInfo.HasGPU = $true
            $gpuInfo.GPUCount = [int]$matches[1]
        }
        
        # Determine GPU type from node info
        if ($nodeInfo -match "Tesla") {
            $gpuInfo.GPUType = "nvidia-tesla"
            $gpuInfo.MemoryGB = 16  # Default for Tesla
        }
        elseif ($nodeInfo -match "RTX.*4090") {
            $gpuInfo.GPUType = "nvidia-rtx"
            $gpuInfo.MemoryGB = 24
        }
        elseif ($nodeInfo -match "RTX.*3090") {
            $gpuInfo.GPUType = "nvidia-rtx"
            $gpuInfo.MemoryGB = 24
        }
        elseif ($nodeInfo -match "RTX.*3080") {
            $gpuInfo.GPUType = "nvidia-rtx"
            $gpuInfo.MemoryGB = 12
        }
        elseif ($nodeInfo -match "GeForce") {
            $gpuInfo.GPUType = "nvidia-geforce"
            $gpuInfo.MemoryGB = 8  # Default for GeForce
        }
        
        return $gpuInfo
    }
    catch {
        Write-Log "Failed to get GPU info for node $NodeName: $_" -Level "ERROR"
        return $null
    }
}

function Label-GPUNode {
    param(
        [string]$NodeName,
        [string]$GPUType,
        [string]$MemoryTier,
        [string]$WorkloadType
    )
    
    Write-Log "Labeling node $NodeName..." -Level "INFO"
    
    $labels = @{
        "accelerator" = "nvidia"
        "gpu-type" = $GPUType
        "gpu-memory" = $MemoryTier
        "workload-type" = $WorkloadType
        "node-type" = "gpu-worker"
        "gameforge.ai/gpu-enabled" = "true"
    }
    
    try {
        foreach ($label in $labels.GetEnumerator()) {
            $command = "kubectl label nodes $NodeName $($label.Key)=$($label.Value) --overwrite"
            if ($DryRun) {
                Write-Log "DRY RUN: $command" -Level "INFO"
            } else {
                Invoke-Expression $command | Out-Null
                Write-Log "Applied label: $($label.Key)=$($label.Value)" -Level "SUCCESS"
            }
        }
        
        # Add taint to ensure only GPU workloads are scheduled
        $taintCommand = "kubectl taint nodes $NodeName nvidia.com/gpu=true:NoSchedule --overwrite"
        if ($DryRun) {
            Write-Log "DRY RUN: $taintCommand" -Level "INFO"
        } else {
            try {
                Invoke-Expression $taintCommand | Out-Null
                Write-Log "Applied GPU taint to prevent non-GPU workloads" -Level "SUCCESS"
            }
            catch {
                Write-Log "Warning: Could not apply taint: $_" -Level "WARN"
            }
        }
        
        return $true
    }
    catch {
        Write-Log "Failed to label node $NodeName: $_" -Level "ERROR"
        return $false
    }
}

function Setup-GPUNodes {
    $nodesToProcess = @()
    
    if ($AutoDetect) {
        $detectedNodes = Get-GPUNodes
        $nodesToProcess += $detectedNodes
    }
    
    if ($NodeNames.Count -gt 0) {
        $nodesToProcess += $NodeNames
    }
    
    if ($nodesToProcess.Count -eq 0) {
        Write-Log "No nodes specified. Use -AutoDetect or specify -NodeNames" -Level "ERROR"
        return $false
    }
    
    # Remove duplicates
    $nodesToProcess = $nodesToProcess | Sort-Object | Get-Unique
    
    Write-Log "Processing $($nodesToProcess.Count) nodes..." -Level "INFO"
    
    $successCount = 0
    $failureCount = 0
    
    foreach ($nodeName in $nodesToProcess) {
        Write-Log "Processing node: $nodeName" -Level "INFO"
        
        # Get node GPU information
        $gpuInfo = Get-NodeGPUInfo -NodeName $nodeName
        
        if ($gpuInfo -and $gpuInfo.HasGPU) {
            Write-Log "Node $nodeName has $($gpuInfo.GPUCount) GPU(s) of type $($gpuInfo.GPUType)" -Level "INFO"
            
            # Determine memory tier based on GPU memory
            $memTier = $MemoryTier
            if ($MemoryTier -eq "auto") {
                if ($gpuInfo.MemoryGB -ge 20) {
                    $memTier = "ultra"
                } elseif ($gpuInfo.MemoryGB -ge 12) {
                    $memTier = "high"
                } elseif ($gpuInfo.MemoryGB -ge 8) {
                    $memTier = "medium"
                } else {
                    $memTier = "low"
                }
            }
            
            # Use detected GPU type if available
            $gpuTypeToUse = if ($gpuInfo.GPUType -ne "unknown") { $gpuInfo.GPUType } else { $GPUType }
            
            if (Label-GPUNode -NodeName $nodeName -GPUType $gpuTypeToUse -MemoryTier $memTier -WorkloadType $WorkloadType) {
                $successCount++
                Write-Log "Successfully configured node $nodeName" -Level "SUCCESS"
            } else {
                $failureCount++
                Write-Log "Failed to configure node $nodeName" -Level "ERROR"
            }
        } else {
            Write-Log "Node $nodeName does not appear to have GPUs" -Level "WARN"
            $failureCount++
        }
    }
    
    Write-Log "Node configuration complete: $successCount successful, $failureCount failed" -Level "INFO"
    return $failureCount -eq 0
}

function Verify-NodeLabels {
    Write-Log "Verifying GPU node labels..." -Level "INFO"
    
    try {
        $gpuNodes = kubectl get nodes -l accelerator=nvidia -o custom-columns="NAME:.metadata.name,GPU-TYPE:.metadata.labels.gpu-type,MEMORY:.metadata.labels.gpu-memory,WORKLOAD:.metadata.labels.workload-type,TAINTS:.spec.taints[*].key" --no-headers 2>$null
        
        if ($gpuNodes) {
            Write-Log "GPU Node Configuration:" -Level "SUCCESS"
            Write-Log "NAME`tGPU-TYPE`tMEMORY`tWORKLOAD`tTAINTS" -Level "INFO"
            $gpuNodes | ForEach-Object { Write-Log $_  -Level "INFO" }
        } else {
            Write-Log "No labeled GPU nodes found" -Level "WARN"
        }
        
        # Check for any unlabeled nodes with GPUs
        $allNodes = kubectl get nodes -o json | ConvertFrom-Json
        foreach ($node in $allNodes.items) {
            $nodeName = $node.metadata.name
            $hasAcceleratorLabel = $node.metadata.labels -and $node.metadata.labels.accelerator
            
            if (-not $hasAcceleratorLabel) {
                $nodeInfo = kubectl describe node $nodeName 2>$null
                if ($nodeInfo -match "nvidia\.com/gpu") {
                    Write-Log "Warning: Node $nodeName has GPUs but is not labeled" -Level "WARN"
                }
            }
        }
    }
    catch {
        Write-Log "Failed to verify node labels: $_" -Level "ERROR"
    }
}

function Remove-GPULabels {
    param([string[]]$NodeNames)
    
    if ($NodeNames.Count -eq 0) {
        Write-Log "Getting all GPU nodes for label removal..." -Level "INFO"
        $NodeNames = kubectl get nodes -l accelerator=nvidia -o jsonpath='{.items[*].metadata.name}' 2>$null
        if ($NodeNames) {
            $NodeNames = $NodeNames -split '\s+'
        } else {
            Write-Log "No GPU nodes found to unlabel" -Level "INFO"
            return
        }
    }
    
    $labelsToRemove = @(
        "accelerator",
        "gpu-type",
        "gpu-memory",
        "workload-type",
        "node-type",
        "gameforge.ai/gpu-enabled"
    )
    
    foreach ($nodeName in $NodeNames) {
        Write-Log "Removing labels from node $nodeName..." -Level "INFO"
        
        foreach ($label in $labelsToRemove) {
            try {
                $command = "kubectl label nodes $nodeName $label-"
                if ($DryRun) {
                    Write-Log "DRY RUN: $command" -Level "INFO"
                } else {
                    Invoke-Expression $command 2>$null | Out-Null
                    Write-Log "Removed label: $label" -Level "SUCCESS"
                }
            }
            catch {
                # Ignore errors for non-existent labels
            }
        }
        
        # Remove taint
        try {
            $taintCommand = "kubectl taint nodes $nodeName nvidia.com/gpu-"
            if ($DryRun) {
                Write-Log "DRY RUN: $taintCommand" -Level "INFO"
            } else {
                Invoke-Expression $taintCommand 2>$null | Out-Null
                Write-Log "Removed GPU taint" -Level "SUCCESS"
            }
        }
        catch {
            # Ignore if taint doesn't exist
        }
    }
}

function Show-Help {
    Write-Host @"
GPU Node Preparation and Labeling Script

USAGE:
    .\setup-gpu-nodes.ps1 [OPTIONS]

OPTIONS:
    -Action <setup|verify|remove>   Action to perform (default: setup)
    -NodeNames <names>              Specific node names to process
    -GPUType <type>                 GPU type (nvidia-tesla, nvidia-rtx, nvidia-geforce)
    -MemoryTier <tier>              Memory tier (low, medium, high, ultra, auto)
    -WorkloadType <type>            Workload type (training, inference, mixed)
    -AutoDetect                     Automatically detect GPU nodes
    -DryRun                         Show what would be done without making changes
    -Verbose                        Enable verbose output

EXAMPLES:
    # Auto-detect and setup all GPU nodes
    .\setup-gpu-nodes.ps1 -AutoDetect

    # Setup specific nodes
    .\setup-gpu-nodes.ps1 -NodeNames node1,node2 -GPUType nvidia-rtx

    # Verify current setup
    .\setup-gpu-nodes.ps1 -Action verify

    # Remove GPU labels
    .\setup-gpu-nodes.ps1 -Action remove -AutoDetect

    # Dry run auto-detection
    .\setup-gpu-nodes.ps1 -AutoDetect -DryRun

LABELS APPLIED:
    accelerator=nvidia              # Identifies GPU nodes
    gpu-type=<type>                 # GPU hardware type
    gpu-memory=<tier>               # Memory capacity tier
    workload-type=<type>            # Intended workload type
    node-type=gpu-worker            # Node role
    gameforge.ai/gpu-enabled=true   # GameForge-specific label

TAINTS APPLIED:
    nvidia.com/gpu=true:NoSchedule  # Prevents non-GPU workloads

"@
}

# Main execution
try {
    Write-Log "🎮 GameForge GPU Node Setup" -Level "INFO"
    Write-Log "Action: $Action" -Level "INFO"
    
    if ($DryRun) {
        Write-Log "DRY RUN MODE - No changes will be made" -Level "WARN"
    }
    
    switch ($Action.ToLower()) {
        "setup" {
            if (Setup-GPUNodes) {
                Write-Log "✅ GPU node setup completed successfully!" -Level "SUCCESS"
                Verify-NodeLabels
            } else {
                Write-Log "❌ GPU node setup completed with errors" -Level "ERROR"
                exit 1
            }
        }
        "verify" {
            Verify-NodeLabels
            Write-Log "✅ GPU node verification completed!" -Level "SUCCESS"
        }
        "remove" {
            $nodesToRemove = @()
            if ($AutoDetect) {
                $nodesToRemove = Get-GPUNodes
            }
            if ($NodeNames.Count -gt 0) {
                $nodesToRemove += $NodeNames
            }
            Remove-GPULabels -NodeNames ($nodesToRemove | Sort-Object | Get-Unique)
            Write-Log "✅ GPU labels removed successfully!" -Level "SUCCESS"
        }
        "help" {
            Show-Help
        }
        default {
            Write-Log "Invalid action: $Action" -Level "ERROR"
            Show-Help
            exit 1
        }
    }
}
catch {
    Write-Log "❌ Operation failed: $_" -Level "ERROR"
    exit 1
}

Write-Log "🚀 GPU node configuration complete!" -Level "SUCCESS"

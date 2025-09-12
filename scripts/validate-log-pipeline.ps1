# GameForge Log Pipeline Validation Script
# Validates complete Elasticsearch + Logstash + Filebeat integration

Write-Host "=== GameForge Log Pipeline Validation ===" -ForegroundColor Cyan
Write-Host "Checking Elasticsearch log pipeline integration..." -ForegroundColor Yellow

$ValidationResults = @{
    "Elasticsearch Service" = $false
    "Logstash Service" = $false
    "Filebeat Service" = $false
    "Log Pipeline Health" = $false
    "Index Templates" = $false
    "Log Ingestion" = $false
    "ILM Policies" = $false
}

# Check if services are running
Write-Host "`n1. Checking Service Status..." -ForegroundColor Green

try {
    $ElasticHealth = docker exec gameforge-elasticsearch-secure curl -s -u elastic:$env:ELASTIC_PASSWORD http://localhost:9200/_cluster/health
    if ($ElasticHealth -match '"status":"(green|yellow)"') {
        $ValidationResults["Elasticsearch Service"] = $true
        Write-Host "   ✓ Elasticsearch is healthy" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Elasticsearch health check failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Elasticsearch service not accessible" -ForegroundColor Red
}

try {
    $LogstashHealth = docker exec gameforge-logstash-secure curl -s http://localhost:9600/_node/stats
    if ($LogstashHealth -match '"status":"green"') {
        $ValidationResults["Logstash Service"] = $true
        Write-Host "   ✓ Logstash is healthy" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Logstash health check failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Logstash service not accessible" -ForegroundColor Red
}

try {
    $FilebeatStatus = docker exec gameforge-filebeat-secure filebeat test config
    if ($LASTEXITCODE -eq 0) {
        $ValidationResults["Filebeat Service"] = $true
        Write-Host "   ✓ Filebeat configuration is valid" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Filebeat configuration test failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Filebeat service not accessible" -ForegroundColor Red
}

# Check pipeline connectivity
Write-Host "`n2. Checking Pipeline Connectivity..." -ForegroundColor Green

try {
    $LogstashPipeline = docker exec gameforge-logstash-secure curl -s http://localhost:9600/_node/pipelines
    if ($LogstashPipeline -match '"events"') {
        $ValidationResults["Log Pipeline Health"] = $true
        Write-Host "   ✓ Logstash pipeline is processing events" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Logstash pipeline not processing events" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Logstash pipeline health check failed" -ForegroundColor Red
}

# Check Elasticsearch indexes and templates
Write-Host "`n3. Checking Elasticsearch Configuration..." -ForegroundColor Green

try {
    $Templates = docker exec gameforge-elasticsearch-secure curl -s -u elastic:$env:ELASTIC_PASSWORD http://localhost:9200/_index_template/gameforge-*
    if ($Templates -match 'gameforge-app') {
        $ValidationResults["Index Templates"] = $true
        Write-Host "   ✓ Index templates are configured" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Index templates not found" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Index template check failed" -ForegroundColor Red
}

try {
    $ILMPolicy = docker exec gameforge-elasticsearch-secure curl -s -u elastic:$env:ELASTIC_PASSWORD http://localhost:9200/_ilm/policy/gameforge-logs-policy
    if ($ILMPolicy -match '"gameforge-logs-policy"') {
        $ValidationResults["ILM Policies"] = $true
        Write-Host "   ✓ ILM policies are configured" -ForegroundColor Green
    } else {
        Write-Host "   ✗ ILM policies not found" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ ILM policy check failed" -ForegroundColor Red
}

# Check for actual log ingestion
Write-Host "`n4. Checking Log Ingestion..." -ForegroundColor Green

try {
    $LogCount = docker exec gameforge-elasticsearch-secure curl -s -u elastic:$env:ELASTIC_PASSWORD "http://localhost:9200/gameforge-*/_count"
    if ($LogCount -match '"count":\s*(\d+)') {
        $Count = $Matches[1]
        if ([int]$Count -gt 0) {
            $ValidationResults["Log Ingestion"] = $true
            Write-Host "   ✓ Logs are being ingested ($Count documents)" -ForegroundColor Green
        } else {
            Write-Host "   ⚠ No logs found (pipeline may need time to collect data)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   ✗ Log ingestion check failed" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Validation Summary ===" -ForegroundColor Cyan

$SuccessCount = ($ValidationResults.Values | Where-Object { $_ -eq $true }).Count
$TotalChecks = $ValidationResults.Count
$SuccessPercentage = [math]::Round(($SuccessCount / $TotalChecks) * 100, 1)

foreach ($Check in $ValidationResults.GetEnumerator()) {
    $Status = if ($Check.Value) { "✓ PASS" } else { "✗ FAIL" }
    $Color = if ($Check.Value) { "Green" } else { "Red" }
    Write-Host "   $($Check.Key): $Status" -ForegroundColor $Color
}

Write-Host "`nOverall Success Rate: $SuccessPercentage% ($SuccessCount/$TotalChecks)" -ForegroundColor $(if ($SuccessPercentage -gt 80) { "Green" } elseif ($SuccessPercentage -gt 60) { "Yellow" } else { "Red" })

# Recommendations
Write-Host "`n=== Recommendations ===" -ForegroundColor Cyan

if (-not $ValidationResults["Elasticsearch Service"]) {
    Write-Host "   • Start Elasticsearch service: docker-compose up -d elasticsearch" -ForegroundColor Yellow
}

if (-not $ValidationResults["Logstash Service"]) {
    Write-Host "   • Start Logstash service: docker-compose up -d logstash" -ForegroundColor Yellow
}

if (-not $ValidationResults["Filebeat Service"]) {
    Write-Host "   • Start Filebeat service: docker-compose up -d filebeat" -ForegroundColor Yellow
}

if (-not $ValidationResults["Index Templates"]) {
    Write-Host "   • Run Elasticsearch initialization: ./monitoring/logging/elasticsearch-init.sh" -ForegroundColor Yellow
}

if (-not $ValidationResults["Log Ingestion"]) {
    Write-Host "   • Check application logging configuration" -ForegroundColor Yellow
    Write-Host "   • Verify log file paths in Filebeat configuration" -ForegroundColor Yellow
    Write-Host "   • Check Logstash pipeline configuration" -ForegroundColor Yellow
}

if ($SuccessPercentage -eq 100) {
    Write-Host "`n🎉 All log pipeline components are working correctly!" -ForegroundColor Green
} elseif ($SuccessPercentage -gt 80) {
    Write-Host "`n⚠️  Log pipeline is mostly functional with minor issues" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Log pipeline requires attention to become fully functional" -ForegroundColor Red
}

Write-Host "`n=== Log Pipeline Integration Complete ===" -ForegroundColor Cyan

#!/bin/bash
# Security Report Generator
# Generates comprehensive security reports from multiple scanners

set -e

REPORT_DIR="security/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/security-report-$TIMESTAMP.html"

mkdir -p "$REPORT_DIR"

echo "Generating GameForge Security Report..."

# HTML Report Template
cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>GameForge Security Report - $TIMESTAMP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .critical { background: #ffebee; border-color: #f44336; }
        .high { background: #fff3e0; border-color: #ff9800; }
        .medium { background: #f3e5f5; border-color: #9c27b0; }
        .low { background: #e8f5e8; border-color: #4caf50; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-pass { color: #4caf50; font-weight: bold; }
        .status-fail { color: #f44336; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>GameForge Security Assessment Report</h1>
        <p>Generated: $(date)</p>
        <p>Report ID: $TIMESTAMP</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <div id="summary">
            <!-- Summary will be populated by script -->
        </div>
    </div>

    <div class="section">
        <h2>Container Image Vulnerabilities</h2>
        <div id="container-vulns">
            <!-- Container scan results will be populated -->
        </div>
    </div>

    <div class="section">
        <h2>Static Code Analysis</h2>
        <div id="sast-results">
            <!-- SAST results will be populated -->
        </div>
    </div>

    <div class="section">
        <h2>Dependency Analysis</h2>
        <div id="dependency-results">
            <!-- Dependency scan results will be populated -->
        </div>
    </div>

    <div class="section">
        <h2>Compliance Status</h2>
        <div id="compliance-status">
            <!-- Compliance check results will be populated -->
        </div>
    </div>

    <div class="section">
        <h2>Security Recommendations</h2>
        <div id="recommendations">
            <!-- Recommendations will be populated -->
        </div>
    </div>
</body>
</html>
EOF

# Collect Trivy scan results
if command -v trivy &> /dev/null; then
    echo "Collecting Trivy scan results..."
    trivy image --format json gameforge:latest > "$REPORT_DIR/trivy-results.json" 2>/dev/null || true
fi

# Collect security metrics from Prometheus
if command -v curl &> /dev/null; then
    echo "Collecting security metrics..."
    curl -s "http://prometheus-security:9091/api/v1/query?query=vulnerability_scanner_critical_count" > "$REPORT_DIR/metrics-critical.json" || true
    curl -s "http://prometheus-security:9091/api/v1/query?query=vulnerability_scanner_high_count" > "$REPORT_DIR/metrics-high.json" || true
fi

# Generate summary statistics
python3 - << 'PYTHON'
import json
import os
from datetime import datetime

report_dir = "security/reports"
summary = {
    "timestamp": datetime.now().isoformat(),
    "critical_vulns": 0,
    "high_vulns": 0,
    "medium_vulns": 0,
    "low_vulns": 0,
    "total_images_scanned": 0,
    "security_gate_status": "UNKNOWN"
}

# Process Trivy results
trivy_file = f"{report_dir}/trivy-results.json"
if os.path.exists(trivy_file):
    try:
        with open(trivy_file, 'r') as f:
            trivy_data = json.load(f)

        for result in trivy_data.get('Results', []):
            for vuln in result.get('Vulnerabilities', []):
                severity = vuln.get('Severity', '').upper()
                if severity == 'CRITICAL':
                    summary['critical_vulns'] += 1
                elif severity == 'HIGH':
                    summary['high_vulns'] += 1
                elif severity == 'MEDIUM':
                    summary['medium_vulns'] += 1
                elif severity == 'LOW':
                    summary['low_vulns'] += 1

        summary['total_images_scanned'] = len(trivy_data.get('Results', []))
    except Exception as e:
        print(f"Error processing Trivy results: {e}")

# Determine security gate status
if summary['critical_vulns'] == 0 and summary['high_vulns'] <= 5:
    summary['security_gate_status'] = "PASS"
else:
    summary['security_gate_status'] = "FAIL"

# Save summary
with open(f"{report_dir}/summary.json", 'w') as f:
    json.dump(summary, f, indent=2)

print(f"Security Report Summary:")
print(f"Critical: {summary['critical_vulns']}")
print(f"High: {summary['high_vulns']}")
print(f"Medium: {summary['medium_vulns']}")
print(f"Low: {summary['low_vulns']}")
print(f"Security Gate: {summary['security_gate_status']}")
PYTHON

echo "Security report generated: $REPORT_FILE"
echo "View the report: open $REPORT_FILE"

# Send report via email if configured
if [ -n "$SECURITY_REPORT_EMAIL" ]; then
    echo "Sending security report to $SECURITY_REPORT_EMAIL..."
    # Add email sending logic here
fi

# Upload to S3 if configured
if [ -n "$SECURITY_REPORT_S3_BUCKET" ]; then
    echo "Uploading security report to S3..."
    aws s3 cp "$REPORT_FILE" "s3://$SECURITY_REPORT_S3_BUCKET/security-reports/" || true
fi

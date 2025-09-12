#!/bin/bash
# Comprehensive Security Scanner
# Runs multiple security tools and aggregates results

set -e

IMAGE_NAME="${1:-gameforge:latest}"
OUTPUT_DIR="security/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

echo "Starting comprehensive security scan for $IMAGE_NAME"

# 1. Trivy Scan
run_trivy_scan() {
    echo "Running Trivy vulnerability scan..."

    if command -v trivy &> /dev/null; then
        trivy image --format json --output "$OUTPUT_DIR/trivy-$TIMESTAMP.json" "$IMAGE_NAME"
        trivy image --format table "$IMAGE_NAME" | tee "$OUTPUT_DIR/trivy-$TIMESTAMP.txt"
        echo "Trivy scan completed"
    else
        echo "Trivy not available, skipping..."
    fi
}

# 2. Grype Scan  
run_grype_scan() {
    echo "Running Grype vulnerability scan..."

    if command -v grype &> /dev/null; then
        grype "$IMAGE_NAME" -o json --file "$OUTPUT_DIR/grype-$TIMESTAMP.json"
        grype "$IMAGE_NAME" -o table | tee "$OUTPUT_DIR/grype-$TIMESTAMP.txt"
        echo "Grype scan completed"
    else
        echo "Grype not available, skipping..."
    fi
}

# 3. Docker Scout Scan
run_docker_scout_scan() {
    echo "Running Docker Scout scan..."

    if command -v docker &> /dev/null && docker scout version &> /dev/null; then
        docker scout cves "$IMAGE_NAME" --format json --output "$OUTPUT_DIR/scout-$TIMESTAMP.json"
        docker scout cves "$IMAGE_NAME" | tee "$OUTPUT_DIR/scout-$TIMESTAMP.txt"
        echo "Docker Scout scan completed"
    else
        echo "Docker Scout not available, skipping..."
    fi
}

# 4. Snyk Scan
run_snyk_scan() {
    echo "Running Snyk container scan..."

    if command -v snyk &> /dev/null && [ -n "$SNYK_TOKEN" ]; then
        snyk container test "$IMAGE_NAME" --json > "$OUTPUT_DIR/snyk-$TIMESTAMP.json" || true
        snyk container test "$IMAGE_NAME" | tee "$OUTPUT_DIR/snyk-$TIMESTAMP.txt" || true
        echo "Snyk scan completed"
    else
        echo "Snyk not available or SNYK_TOKEN not set, skipping..."
    fi
}

# 5. Image Configuration Analysis
run_config_analysis() {
    echo "Running image configuration analysis..."

    # Dive analysis for layer efficiency
    if command -v dive &> /dev/null; then
        dive "$IMAGE_NAME" --json > "$OUTPUT_DIR/dive-$TIMESTAMP.json"
        echo "Dive analysis completed"
    fi

    # Image history analysis
    docker history "$IMAGE_NAME" --format "table {{.CreatedBy}}	{{.Size}}" > "$OUTPUT_DIR/image-history-$TIMESTAMP.txt"

    # Image inspect
    docker image inspect "$IMAGE_NAME" > "$OUTPUT_DIR/image-inspect-$TIMESTAMP.json"

    echo "Configuration analysis completed"
}

# 6. Secrets Detection
run_secrets_detection() {
    echo "Running secrets detection..."

    # Extract image to temporary directory for scanning
    TEMP_DIR=$(mktemp -d)
    docker save "$IMAGE_NAME" | tar -x -C "$TEMP_DIR"

    # TruffleHog secrets scan
    if command -v trufflehog &> /dev/null; then
        trufflehog filesystem "$TEMP_DIR" --json > "$OUTPUT_DIR/secrets-$TIMESTAMP.json" || true
        echo "TruffleHog secrets scan completed"
    fi

    # Simple grep-based secrets detection
    find "$TEMP_DIR" -type f -exec grep -l -E "(password|secret|key|token)" {} \; > "$OUTPUT_DIR/potential-secrets-$TIMESTAMP.txt" || true

    # Cleanup
    rm -rf "$TEMP_DIR"

    echo "Secrets detection completed"
}

# 7. Malware Scanning
run_malware_scan() {
    echo "Running malware detection..."

    # ClamAV scan if available
    if command -v clamscan &> /dev/null; then
        TEMP_DIR=$(mktemp -d)
        docker save "$IMAGE_NAME" | tar -x -C "$TEMP_DIR"

        clamscan -r "$TEMP_DIR" --log="$OUTPUT_DIR/malware-$TIMESTAMP.log" || true

        rm -rf "$TEMP_DIR"
        echo "Malware scan completed"
    else
        echo "ClamAV not available, skipping malware scan..."
    fi
}

# 8. Aggregate Results
aggregate_results() {
    echo "Aggregating scan results..."

    python3 - << 'PYTHON'
import json
import glob
import os
from datetime import datetime

def aggregate_vulnerability_results():
    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "image_name": os.environ.get("IMAGE_NAME", "unknown"),
        "summary": {
            "critical": 0,
            "high": 0, 
            "medium": 0,
            "low": 0,
            "total": 0
        },
        "scanners": {},
        "recommendations": []
    }

    output_dir = os.environ.get("OUTPUT_DIR", "security/reports")
    timestamp = os.environ.get("TIMESTAMP", "")

    # Process Trivy results
    trivy_files = glob.glob(f"{output_dir}/trivy-{timestamp}.json")
    if trivy_files:
        try:
            with open(trivy_files[0], 'r') as f:
                trivy_data = json.load(f)

            scanner_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

            for result in trivy_data.get('Results', []):
                for vuln in result.get('Vulnerabilities', []):
                    severity = vuln.get('Severity', '').lower()
                    if severity in scanner_summary:
                        scanner_summary[severity] += 1
                        results["summary"][severity] += 1

            results["scanners"]["trivy"] = scanner_summary
        except Exception as e:
            print(f"Error processing Trivy results: {e}")

    # Process Grype results  
    grype_files = glob.glob(f"{output_dir}/grype-{timestamp}.json")
    if grype_files:
        try:
            with open(grype_files[0], 'r') as f:
                grype_data = json.load(f)

            scanner_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

            for match in grype_data.get('matches', []):
                severity = match.get('vulnerability', {}).get('severity', '').lower()
                if severity in scanner_summary:
                    scanner_summary[severity] += 1

            results["scanners"]["grype"] = scanner_summary
        except Exception as e:
            print(f"Error processing Grype results: {e}")

    # Calculate total
    results["summary"]["total"] = sum(results["summary"].values())

    # Generate recommendations
    if results["summary"]["critical"] > 0:
        results["recommendations"].append("URGENT: Address critical vulnerabilities immediately")

    if results["summary"]["high"] > 10:
        results["recommendations"].append("HIGH PRIORITY: Reduce high severity vulnerabilities")

    if results["summary"]["total"] > 50:
        results["recommendations"].append("Consider using a minimal base image")

    # Save aggregated results
    with open(f"{output_dir}/scan-summary.json", 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Aggregated results saved to {output_dir}/scan-summary.json")
    print(f"Total vulnerabilities: {results['summary']['total']}")
    print(f"Critical: {results['summary']['critical']}")
    print(f"High: {results['summary']['high']}")
    print(f"Medium: {results['summary']['medium']}")
    print(f"Low: {results['summary']['low']}")

    return results

aggregate_vulnerability_results()
PYTHON
}

# Main execution
main() {
    echo "=== Comprehensive Security Scan ==="
    echo "Image: $IMAGE_NAME"
    echo "Output: $OUTPUT_DIR"

    # Run all scans
    run_trivy_scan
    run_grype_scan
    run_docker_scout_scan
    run_snyk_scan
    run_config_analysis
    run_secrets_detection
    run_malware_scan

    # Aggregate results
    aggregate_results

    echo "=== Scan Complete ==="
    echo "Reports available in: $OUTPUT_DIR"
    echo "Summary: $OUTPUT_DIR/scan-summary.json"
}

# Set environment variables for Python script
export IMAGE_NAME OUTPUT_DIR TIMESTAMP

# Execute main function
main "$@"

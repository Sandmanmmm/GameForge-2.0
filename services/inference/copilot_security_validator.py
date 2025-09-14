#!/usr/bin/env python3
"""
GameForge Copilot Security Validation
=====================================

Copilot security checks for model inference service:
1. Verify each manifest has weights_sha256 and license
2. Flag any manifest lacking checksums or pointing to local file:// paths
3. Validate model loading code security practices

This script implements the exact Copilot validation requirements.
"""

import sys
import os
import ast
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse

# Add the services directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from services.inference.model_manager import ModelManager
except ImportError:
    print("Warning: Could not import ModelManager - running standalone")
    ModelManager = None


class CopilotSecurityValidator:
    """
    Copilot Security Validator for GameForge Inference Service
    
    Implements the exact validation requirements from the Copilot prompt:
    - Verify each manifest has weights_sha256 and license
    - Flag any manifest lacking checksums or pointing to local file:// paths
    - Validate model loading code for security practices
    """
    
    def __init__(self,
                 manifest_dir: str = "models/manifests",
                 inference_dir: str = "services/inference"):
        self.manifest_dir = Path(manifest_dir)
        self.inference_dir = Path(inference_dir)
        self.results = {
            "manifest_validation": {},
            "code_validation": {},
            "overall_score": 0.0,
            "security_issues": [],
            "recommendations": []
        }
    
    def validate_manifests(self) -> Dict[str, Any]:
        """
        Copilot Check: Verify each manifest has weights_sha256 and license.
        Flag any manifest lacking checksums or pointing to local file:// paths.
        """
        print("🔍 Running Copilot manifest security validation...")
        
        yaml_files = list(self.manifest_dir.glob("*.yaml"))
        yml_files = list(self.manifest_dir.glob("*.yml"))
        manifest_files = yaml_files + yml_files
        
        if not manifest_files:
            self.results["security_issues"].append("No manifest files found")
            return self.results["manifest_validation"]
        
        total_manifests = len(manifest_files)
        valid_manifests = 0
        violations = {}
        
        for manifest_file in manifest_files:
            model_name = manifest_file.stem
            issues = self._validate_single_manifest(manifest_file)
            
            if issues:
                violations[model_name] = issues
            else:
                valid_manifests += 1
        
        # Calculate security score
        if total_manifests > 0:
            security_score = valid_manifests / total_manifests
        else:
            security_score = 0.0
        
        self.results["manifest_validation"] = {
            "total_manifests": total_manifests,
            "valid_manifests": valid_manifests,
            "invalid_manifests": total_manifests - valid_manifests,
            "security_score": security_score,
            "violations": violations
        }
        
        # Add overall assessment
        if security_score == 1.0:
            print("✅ All manifests pass Copilot security validation")
        elif security_score >= 0.8:
            print(f"⚠️  Most manifests valid "
                  f"({security_score:.1%}) - some issues found")
        else:
            print(f"❌ Critical security issues in manifests "
                  f"({security_score:.1%})")
            msg = f"Low manifest security score: {security_score:.1%}"
            self.results["security_issues"].append(msg)
        
        return self.results["manifest_validation"]
    
    def _validate_single_manifest(self, manifest_file: Path) -> List[str]:
        """Validate a single manifest file against Copilot requirements"""
        issues = []
        
        try:
            with open(manifest_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Check for weights_sha256 field
            if 'weights_sha256' not in data:
                issues.append("Missing weights_sha256 field")
            elif not data['weights_sha256']:
                issues.append("Empty weights_sha256 field")
            elif len(str(data['weights_sha256'])) != 64:
                issues.append("Invalid weights_sha256 format (not 64 chars)")
            
            # Check for license field
            if 'license' not in data:
                issues.append("Missing license field")
            elif not data['license']:
                issues.append("Empty license field")
            elif str(data['license']).lower() in ['none', 'unknown', '']:
                issues.append("License cannot be 'none', 'unknown', or empty")
            
            # Check weights URI for local file:// paths
            if 'weights_uri' in data:
                uri = data['weights_uri']
                parsed_uri = urlparse(uri)
                if parsed_uri.scheme == 'file' or not parsed_uri.scheme:
                    issues.append(f"Local file:// URI not allowed: {uri}")
                elif parsed_uri.scheme not in ['https', 's3', 'gs', 'azure']:
                    msg = f"Unsupported URI scheme: {parsed_uri.scheme}"
                    issues.append(msg)
            else:
                issues.append("Missing weights_uri field")
            
            # Check delta security
            if 'deltas' in data and isinstance(data['deltas'], list):
                for i, delta in enumerate(data['deltas']):
                    if 'sha256' not in delta:
                        issues.append(f"Delta {i+1} missing SHA256")
                    elif len(str(delta['sha256'])) != 64:
                        issues.append(f"Delta {i+1} invalid SHA256 format")
                    
                    if 'uri' in delta:
                        delta_uri = urlparse(delta['uri'])
                        if delta_uri.scheme == 'file' or not delta_uri.scheme:
                            uri_msg = (f"Delta {i+1} has local file:// URI: "
                                       f"{delta['uri']}")
                            issues.append(uri_msg)
            
        except yaml.YAMLError:
            issues.append("Invalid YAML format")
        except Exception as e:
            issues.append(f"Error reading manifest: {str(e)}")
        
        return issues
    
    def validate_model_loading_code(self) -> Dict[str, Any]:
        """
        Copilot Check: Find code that loads model files. Ensure model
        URIs are not local repo paths, that weights are verified by
        SHA256 before loading, and that there's code to compose LoRA
        deltas without writing raw combined models to disk.
        """
        print("🔍 Running Copilot code security validation...")
        
        python_files = list(self.inference_dir.glob("**/*.py"))
        
        total_files = len(python_files)
        security_violations = []
        good_practices = []
        
        for py_file in python_files:
            violations, practices = self._validate_python_file(py_file)
            security_violations.extend(violations)
            good_practices.extend(practices)
        
        # Calculate code security score
        total_items = len(security_violations) + len(good_practices)
        if total_items > 0:
            code_score = len(good_practices) / total_items
        else:
            code_score = 1.0
        
        self.results["code_validation"] = {
            "files_scanned": total_files,
            "security_violations": security_violations,
            "good_practices": good_practices,
            "security_score": code_score
        }
        
        # Assess code security
        if not security_violations:
            print("✅ All code passes Copilot security validation")
        else:
            violations_count = len(security_violations)
            print(f"⚠️  Found {violations_count} security issues in code")
            for violation in security_violations:
                desc = violation['description']
                self.results["security_issues"].append(desc)
        
        return self.results["code_validation"]
    
    def _validate_python_file(self, py_file: Path) -> tuple:
        """Validate a Python file for security practices"""
        violations = []
        good_practices = []
        
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Look for security patterns
            for node in ast.walk(tree):
                # Check for file:// URIs in string literals
                if isinstance(node, ast.Str) and 'file://' in node.s:
                    violations.append({
                        "file": str(py_file),
                        "line": node.lineno,
                        "description": f"Local file:// URI found: {node.s}",
                        "type": "local_file_uri"
                    })
                
                # Check for SHA256 verification patterns
                if isinstance(node, ast.Call) and hasattr(node.func, 'attr'):
                    if 'sha256' in str(node.func.attr).lower():
                        good_practices.append({
                            "file": str(py_file),
                            "line": node.lineno,
                            "description": "SHA256 verification found",
                            "type": "checksum_verification"
                        })
                    
                    # Check for unsafe model loading
                    if 'load' in str(node.func.attr).lower():
                        # Look for potentially unsafe loading patterns
                        for arg in node.args:
                            if isinstance(arg, ast.Str):
                                unsafe_paths = ['./', '../', '/tmp/',
                                                '/var/tmp/']
                                unsafe_found = any(unsafe in arg.s
                                                   for unsafe in unsafe_paths)
                                if unsafe_found:
                                    violations.append({
                                        "file": str(py_file),
                                        "line": node.lineno,
                                        "description": (
                                            f"Potentially unsafe model path: "
                                            f"{arg.s}"
                                        ),
                                        "type": "unsafe_path"
                                    })
            
            # Check for in-memory LoRA composition (good practice)
            if 'lora' in content.lower() and 'disk' not in content.lower():
                good_practices.append({
                    "file": str(py_file),
                    "line": 0,
                    "description": "In-memory LoRA composition detected",
                    "type": "memory_only_lora"
                })
            
            # Check for proper model verification
            if 'verify_file_checksum' in content:
                good_practices.append({
                    "file": str(py_file),
                    "line": 0,
                    "description": "Model checksum verification implemented",
                    "type": "model_verification"
                })
            
            # Check for secure URI handling
            if 'urlparse' in content and 'file' in content:
                good_practices.append({
                    "file": str(py_file),
                    "line": 0,
                    "description": "Secure URI parsing with file:// filtering",
                    "type": "secure_uri_handling"
                })
        
        except Exception as e:
            violations.append({
                "file": str(py_file),
                "line": 0,
                "description": f"Code analysis error: {str(e)}",
                "type": "analysis_error"
            })
        
        return violations, good_practices
    
    def generate_copilot_report(self) -> Dict[str, Any]:
        """Generate comprehensive Copilot security validation report"""
        print("\n📊 Generating Copilot Security Report...")
        
        # Run all validations
        self.validate_manifests()
        self.validate_model_loading_code()
        
        # Calculate overall security score
        manifest_validation = self.results["manifest_validation"]
        manifest_score = manifest_validation.get("security_score", 0.0)
        code_score = self.results["code_validation"].get("security_score", 0.0)
        overall_score = (manifest_score + code_score) / 2
        
        self.results["overall_score"] = overall_score
        
        # Generate recommendations
        if manifest_score < 1.0:
            msg = ("Fix manifest security issues: ensure all manifests have "
                   "weights_sha256 and license fields")
            self.results["recommendations"].append(msg)
        
        if code_score < 1.0:
            msg = ("Improve code security: remove local file:// URIs and "
                   "add SHA256 verification")
            self.results["recommendations"].append(msg)
        
        if overall_score >= 0.9:
            status = "✅ EXCELLENT"
        elif overall_score >= 0.7:
            status = "⚠️  GOOD"
        elif overall_score >= 0.5:
            status = "🔶 NEEDS IMPROVEMENT"
        else:
            status = "❌ CRITICAL ISSUES"
        
        print(f"\n🎯 Copilot Security Score: {overall_score:.1%} {status}")
        
        return self.results
    
    def save_report(self, output_file: str = "copilot_security_report.json"):
        """Save the validation report to a JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"📄 Report saved to {output_file}")


def main():
    """Main entry point for Copilot security validation"""
    print("🚀 GameForge Copilot Security Validation")
    print("=" * 50)
    
    # Initialize validator
    validator = CopilotSecurityValidator()
    
    # Generate comprehensive report
    report = validator.generate_copilot_report()
    
    # Print summary
    print("\n📋 COPILOT VALIDATION SUMMARY")
    print("-" * 30)
    
    manifest_results = report["manifest_validation"]
    if manifest_results:
        valid = manifest_results['valid_manifests']
        total = manifest_results['total_manifests']
        print(f"Manifests: {valid}/{total} valid")
    
    code_results = report["code_validation"]
    if code_results:
        print(f"Code Files: {code_results['files_scanned']} scanned")
        print(f"Security Issues: {len(code_results['security_violations'])}")
        print(f"Good Practices: {len(code_results['good_practices'])}")
    
    print(f"Overall Score: {report['overall_score']:.1%}")
    
    # Print violations
    if report["security_issues"]:
        print("\n🚨 SECURITY ISSUES FOUND:")
        for issue in report["security_issues"]:
            print(f"  • {issue}")
    
    # Print recommendations
    if report["recommendations"]:
        print("\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
    
    # Save detailed report
    validator.save_report()
    
    # Exit with appropriate code
    if report["overall_score"] >= 0.8:
        print("\n✅ Copilot validation PASSED")
        sys.exit(0)
    else:
        print("\n❌ Copilot validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

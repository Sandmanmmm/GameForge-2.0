#!/usr/bin/env python3
"""
GameForge Copilot Security Validation for Super-Resolution Service
=================================================================

Validates that no large binary model files are tracked in git repository.
Ensures compliance with security policies for model file management.

This script checks:
- No *.pth, *.safetensors, *.bin, *.ckpt files in git
- Model manifests reference remote URIs only
- SHA256 checksums are present and valid format
- License compliance for all model configurations

Usage:
    python validate_superres_security.py
    
Exit codes:
    0 = All validations passed
    1 = Security violations found
    2 = Script execution error
"""

import sys
import re
import yaml
import subprocess
from pathlib import Path


class SuperResSecurityValidator:
    """Security validator for super-resolution service"""
    
    def __init__(self, repo_root: str = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.errors = []
        self.warnings = []
        
        # Prohibited file patterns in git
        self.prohibited_patterns = [
            r'\.pth$',
            r'\.safetensors$',
            r'\.bin$',
            r'\.ckpt$',
            r'\.pt$',
            r'\.pkl$',
            r'\.h5$',
            r'\.hdf5$',
            r'\.tflite$',
            r'\.onnx$'
        ]
        
        # Required manifest fields
        self.required_manifest_fields = [
            'weights_uri',
            'weights_sha256',
            'license',
            'model_name'
        ]
    
    def validate_all(self) -> bool:
        """Run all security validations"""
        print("🔍 Starting GameForge Super-Resolution Security Validation")
        print(f"📁 Repository root: {self.repo_root}")
        
        # Check git status
        if not self._is_git_repository():
            self.errors.append("Not a git repository")
            return False
        
        # Run individual checks
        self._check_git_tracked_files()
        self._validate_model_manifests()
        self._check_superres_service()
        self._validate_gitignore_patterns()
        
        # Report results
        self._print_results()
        
        return len(self.errors) == 0
    
    def _is_git_repository(self) -> bool:
        """Check if current directory is a git repository"""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_root,
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_git_tracked_files(self):
        """Check for prohibited model files in git"""
        print("🔍 Checking git-tracked files...")
        
        try:
            # Get all tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            tracked_files = result.stdout.strip().split('\n')
            
            # Check each file against prohibited patterns
            violations = []
            for file_path in tracked_files:
                for pattern in self.prohibited_patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        violations.append(file_path)
                        break
            
            if violations:
                self.errors.append(
                    f"Prohibited model files found in git: {violations}")
                for violation in violations:
                    print(f"❌ Prohibited file tracked: {violation}")
            else:
                print("✅ No prohibited model files found in git")
                
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to check git files: {e}")
    
    def _validate_model_manifests(self):
        """Validate model manifest files"""
        print("🔍 Validating model manifests...")
        
        manifests_dir = self.repo_root / "models" / "manifests"
        
        if not manifests_dir.exists():
            self.warnings.append("Models manifests directory not found")
            return
        
        manifest_files = list(manifests_dir.glob("*.yaml")) + \
                        list(manifests_dir.glob("*.yml"))
        
        if not manifest_files:
            self.warnings.append("No model manifest files found")
            return
        
        for manifest_file in manifest_files:
            self._validate_single_manifest(manifest_file)
    
    def _validate_single_manifest(self, manifest_path: Path):
        """Validate a single model manifest file"""
        try:
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
            
            if not isinstance(manifest, dict):
                self.errors.append(
                    f"Invalid manifest format: {manifest_path}")
                return
            
            # Check required fields
            for field in self.required_manifest_fields:
                if field not in manifest:
                    self.errors.append(
                        f"Missing required field '{field}' in {manifest_path}")
            
            # Validate weights URI (must be remote)
            if 'weights_uri' in manifest:
                uri = manifest['weights_uri']
                if self._is_local_uri(uri):
                    self.errors.append(
                        f"Local URI not allowed in {manifest_path}: {uri}")
            
            # Validate SHA256 format
            if 'weights_sha256' in manifest:
                sha256 = manifest['weights_sha256']
                if not self._is_valid_sha256(sha256):
                    self.errors.append(
                        f"Invalid SHA256 format in {manifest_path}")
            
            # Check license field
            if 'license' in manifest:
                license_val = manifest['license']
                if not license_val or license_val.lower() in ['none', 'unknown', '']:
                    self.warnings.append(
                        f"Missing or unclear license in {manifest_path}")
            
            print(f"✅ Manifest validated: {manifest_path.name}")
            
        except Exception as e:
            self.errors.append(
                f"Failed to validate manifest {manifest_path}: {e}")
    
    def _is_local_uri(self, uri: str) -> bool:
        """Check if URI is local (prohibited)"""
        return (uri.startswith('file://') or 
                uri.startswith('/') or 
                uri.startswith('./') or 
                uri.startswith('../') or
                (len(uri) > 1 and uri[1] == ':'))  # Windows path
    
    def _is_valid_sha256(self, sha256: str) -> bool:
        """Validate SHA256 format"""
        return (isinstance(sha256, str) and 
                len(sha256) == 64 and 
                all(c in '0123456789abcdefABCDEF' for c in sha256))
    
    def _check_superres_service(self):
        """Check super-resolution service implementation"""
        print("🔍 Checking super-resolution service...")
        
        service_dir = self.repo_root / "services" / "superres"
        
        if not service_dir.exists():
            self.warnings.append("Super-resolution service directory not found")
            return
        
        # Check required files
        required_files = ["server.py", "requirements.txt"]
        for file_name in required_files:
            file_path = service_dir / file_name
            if not file_path.exists():
                self.errors.append(f"Missing required file: {file_path}")
            else:
                print(f"✅ Found service file: {file_name}")
        
        # Check server.py for security patterns
        server_file = service_dir / "server.py"
        if server_file.exists():
            self._validate_server_security(server_file)
    
    def _validate_server_security(self, server_file: Path):
        """Validate server.py security patterns"""
        try:
            with open(server_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for security patterns
            security_checks = [
                ('SHA256 verification', r'sha256|checksum'),
                ('License validation', r'license'),
                ('Remote URI only', r'weights_uri|download.*model'),
                ('No local file tracking', r'file://.*not.*allowed|no.*local.*file')
            ]
            
            for check_name, pattern in security_checks:
                if re.search(pattern, content, re.IGNORECASE):
                    print(f"✅ Security pattern found: {check_name}")
                else:
                    self.warnings.append(
                        f"Security pattern not found in server.py: {check_name}")
            
        except Exception as e:
            self.errors.append(f"Failed to validate server.py: {e}")
    
    def _validate_gitignore_patterns(self):
        """Check .gitignore has model file patterns"""
        print("🔍 Checking .gitignore patterns...")
        
        gitignore_file = self.repo_root / ".gitignore"
        
        if not gitignore_file.exists():
            self.warnings.append(".gitignore file not found")
            return
        
        try:
            with open(gitignore_file, 'r') as f:
                gitignore_content = f.read()
            
            # Recommended patterns for model files
            recommended_patterns = [
                "*.pth",
                "*.safetensors", 
                "*.bin",
                "*.ckpt"
            ]
            
            missing_patterns = []
            for pattern in recommended_patterns:
                if pattern not in gitignore_content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                self.warnings.append(
                    f"Consider adding to .gitignore: {missing_patterns}")
            else:
                print("✅ Model file patterns found in .gitignore")
                
        except Exception as e:
            self.warnings.append(f"Failed to check .gitignore: {e}")
    
    def _print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("🔒 GAMEFORGE SUPER-RESOLUTION SECURITY VALIDATION RESULTS")
        print("="*60)
        
        if self.errors:
            print(f"\n❌ ERRORS FOUND ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ ALL SECURITY VALIDATIONS PASSED!")
            print("   Super-resolution service is compliant with security policies.")
        elif not self.errors:
            print(f"\n✅ SECURITY VALIDATION PASSED (with {len(self.warnings)} warnings)")
            print("   No critical security violations found.")
        else:
            print(f"\n❌ SECURITY VALIDATION FAILED!")
            print(f"   {len(self.errors)} error(s) must be resolved.")
        
        print("\n" + "="*60)


def main():
    """Main execution function"""
    try:
        # Parse command line arguments
        repo_root = sys.argv[1] if len(sys.argv) > 1 else None
        
        # Run validation
        validator = SuperResSecurityValidator(repo_root)
        success = validator.validate_all()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"❌ Validation script error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
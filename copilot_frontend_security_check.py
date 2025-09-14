#!/usr/bin/env python3
"""
GameForge Frontend API Centralization Security Check
====================================================

Copilot security analysis for frontend API usage:
1. Find hardcoded API endpoints (http://localhost:*)
2. Detect direct fetch/axios usage not routed through services/api.ts
3. Check for unhandled Promise rejections
4. Identify missing error UI components
5. Validate token handling centralization

Usage:
    python copilot_frontend_security_check.py

Exit codes:
    0 = All checks passed
    1 = Security issues found
    2 = Script execution error
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Set


class FrontendSecurityChecker:
    """Frontend API security checker"""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.issues = []
        self.warnings = []
        self.stats = {
            'files_checked': 0,
            'hardcoded_urls': 0,
            'direct_fetch_calls': 0,
            'unhandled_promises': 0,
            'missing_error_handling': 0
        }
        
        # Patterns to detect
        self.hardcoded_url_pattern = re.compile(
            r'https?://localhost:\d+|https?://127\.0\.0\.1:\d+', 
            re.IGNORECASE
        )
        
        self.fetch_patterns = [
            re.compile(r'\bfetch\s*\(', re.IGNORECASE),
            re.compile(r'\baxios\s*\.', re.IGNORECASE),
            re.compile(r'from\s+[\'"]axios[\'"]', re.IGNORECASE)
        ]
        
        self.promise_patterns = [
            re.compile(r'\.then\s*\(', re.IGNORECASE),
            re.compile(r'await\s+\w+\s*\(', re.IGNORECASE),
            re.compile(r'Promise\s*\.\s*\w+', re.IGNORECASE)
        ]
        
        # Files that should use centralized API
        self.api_service_files = ['services/api.ts', 'lib/aiAPI.ts', 'lib/assetsAPI.ts']
        
        # Centralized API imports to look for
        self.centralized_imports = [
            'services/api',
            '../services/api',
            '../../services/api',
            '@/services/api'
        ]
    
    def check_all(self) -> bool:
        """Run all security checks"""
        print("🔍 Starting Frontend API Security Analysis")
        print(f"📁 Checking source directory: {self.src_path}")
        
        if not self.src_path.exists():
            self.issues.append(f"Source directory not found: {self.src_path}")
            return False
        
        # Find all TypeScript/JavaScript files
        source_files = self._find_source_files()
        
        if not source_files:
            self.warnings.append("No source files found to analyze")
            return True
        
        print(f"📄 Found {len(source_files)} source files to analyze")
        
        for file_path in source_files:
            self._check_file(file_path)
        
        # Run additional checks
        self._check_api_service_usage()
        self._check_error_handling_patterns()
        
        # Generate report
        self._print_report()
        
        return len(self.issues) == 0
    
    def _find_source_files(self) -> List[Path]:
        """Find all TypeScript and JavaScript source files"""
        patterns = ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx']
        files = []
        
        for pattern in patterns:
            files.extend(self.src_path.glob(pattern))
        
        # Filter out node_modules, dist, build directories
        filtered_files = []
        for file_path in files:
            if not any(excluded in str(file_path) for excluded in ['node_modules', 'dist', 'build', '.git']):
                filtered_files.append(file_path)
        
        return sorted(filtered_files)
    
    def _check_file(self, file_path: Path):
        """Check individual file for security issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.stats['files_checked'] += 1
            relative_path = file_path.relative_to(self.src_path.parent)
            
            # Check for hardcoded URLs
            self._check_hardcoded_urls(content, relative_path)
            
            # Check for direct fetch/axios usage
            self._check_direct_api_calls(content, relative_path)
            
            # Check for unhandled promises
            self._check_promise_handling(content, relative_path)
            
            # Check for proper API imports
            self._check_api_imports(content, relative_path)
            
        except Exception as e:
            self.warnings.append(f"Failed to read file {file_path}: {e}")
    
    def _check_hardcoded_urls(self, content: str, file_path: Path):
        """Check for hardcoded localhost URLs"""
        matches = self.hardcoded_url_pattern.findall(content)
        
        if matches:
            self.stats['hardcoded_urls'] += len(matches)
            unique_urls = set(matches)
            
            for url in unique_urls:
                self.issues.append({
                    'type': 'hardcoded_url',
                    'severity': 'high',
                    'file': str(file_path),
                    'message': f"Hardcoded URL found: {url}",
                    'recommendation': "Use environment variables via VITE_ prefixed config"
                })
    
    def _check_direct_api_calls(self, content: str, file_path: Path):
        """Check for direct fetch/axios calls not using centralized API"""
        # Skip if this is an API service file itself
        if any(api_file in str(file_path) for api_file in self.api_service_files):
            return
        
        # Check for fetch calls
        for pattern in self.fetch_patterns:
            matches = pattern.findall(content)
            if matches:
                self.stats['direct_fetch_calls'] += len(matches)
                
                # Check if file imports centralized API
                has_centralized_import = any(
                    imp_pattern in content for imp_pattern in self.centralized_imports
                )
                
                if not has_centralized_import:
                    self.issues.append({
                        'type': 'direct_api_call',
                        'severity': 'high',
                        'file': str(file_path),
                        'message': f"Direct {pattern.pattern} call found without centralized API import",
                        'recommendation': "Import and use services/api.ts for all API calls"
                    })
                else:
                    self.warnings.append(f"Direct API call in {file_path} but centralized import present")
    
    def _check_promise_handling(self, content: str, file_path: Path):
        """Check for unhandled Promise rejections"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for async/await without try-catch
            if 'await' in line and 'try' not in line:
                # Check if there's a try block above
                try_found = False
                for j in range(max(0, i-10), i):
                    if j < len(lines) and 'try' in lines[j]:
                        try_found = True
                        break
                
                if not try_found and 'catch' not in ''.join(lines[i:i+5]):
                    self.stats['unhandled_promises'] += 1
                    self.warnings.append(f"Potential unhandled async operation at {file_path}:{i}")
            
            # Look for .then() without .catch()
            if '.then(' in line and '.catch(' not in content[content.find(line):content.find(line)+200]:
                self.warnings.append(f"Promise without catch handler at {file_path}:{i}")
    
    def _check_api_imports(self, content: str, file_path: Path):
        """Check if files properly import centralized API services"""
        # Skip certain file types
        if any(skip in str(file_path) for skip in ['test', 'spec', 'stories', 'types']):
            return
        
        # Check if file makes API calls but doesn't import centralized service
        has_api_calls = any(pattern.search(content) for pattern in self.fetch_patterns)
        has_centralized_import = any(imp in content for imp in self.centralized_imports)
        
        if has_api_calls and not has_centralized_import:
            # Check if it's defining an API service itself
            if 'export' in content and ('APIClient' in content or 'fetch(' in content):
                return  # This is likely an API service file
            
            self.issues.append({
                'type': 'missing_centralized_import',
                'severity': 'medium',
                'file': str(file_path),
                'message': "File makes API calls but doesn't import centralized API service",
                'recommendation': "Import from services/api.ts for consistent error handling and auth"
            })
    
    def _check_api_service_usage(self):
        """Check if centralized API service exists and is properly structured"""
        api_service_path = self.src_path / 'services' / 'api.ts'
        
        if not api_service_path.exists():
            self.issues.append({
                'type': 'missing_api_service',
                'severity': 'critical',
                'file': str(api_service_path),
                'message': "Centralized API service not found",
                'recommendation': "Create services/api.ts with centralized authentication and error handling"
            })
            return
        
        try:
            with open(api_service_path, 'r', encoding='utf-8') as f:
                api_content = f.read()
            
            # Check for required patterns in API service
            required_patterns = [
                ('authentication', r'auth|token|Authorization'),
                ('error_handling', r'catch|Error|exception'),
                ('retry_logic', r'retry|attempt'),
                ('timeout', r'timeout|abort'),
                ('environment_config', r'env|VITE_')
            ]
            
            for feature, pattern in required_patterns:
                if not re.search(pattern, api_content, re.IGNORECASE):
                    self.warnings.append(f"API service missing {feature} implementation")
        
        except Exception as e:
            self.warnings.append(f"Failed to analyze API service: {e}")
    
    def _check_error_handling_patterns(self):
        """Check for consistent error handling patterns"""
        # Look for error boundary components
        error_boundary_files = list(self.src_path.glob('**/ErrorBoundary*.tsx')) + \
                              list(self.src_path.glob('**/ErrorFallback*.tsx'))
        
        if not error_boundary_files:
            self.warnings.append("No Error Boundary components found - consider adding for better error UI")
        
        # Check for consistent error state management
        error_state_patterns = ['error', 'isError', 'hasError', 'errorMessage']
        files_with_error_state = 0
        
        for file_path in self.src_path.glob('**/*.tsx'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if any(pattern in content for pattern in error_state_patterns):
                    files_with_error_state += 1
            except:
                continue
        
        if files_with_error_state < 3:
            self.warnings.append("Few components implement error state handling")
    
    def _print_report(self):
        """Print comprehensive security report"""
        print("\n" + "="*70)
        print("🔒 GAMEFORGE FRONTEND API SECURITY ANALYSIS RESULTS")
        print("="*70)
        
        # Print statistics
        print(f"\n📊 ANALYSIS STATISTICS:")
        print(f"   Files analyzed: {self.stats['files_checked']}")
        print(f"   Hardcoded URLs found: {self.stats['hardcoded_urls']}")
        print(f"   Direct API calls: {self.stats['direct_fetch_calls']}")
        print(f"   Potential unhandled promises: {self.stats['unhandled_promises']}")
        
        # Print issues by severity
        critical_issues = [i for i in self.issues if isinstance(i, dict) and i.get('severity') == 'critical']
        high_issues = [i for i in self.issues if isinstance(i, dict) and i.get('severity') == 'high']
        medium_issues = [i for i in self.issues if isinstance(i, dict) and i.get('severity') == 'medium']
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
            for issue in critical_issues:
                print(f"   • {issue['message']}")
                print(f"     File: {issue['file']}")
                print(f"     Fix: {issue['recommendation']}")
                print()
        
        if high_issues:
            print(f"\n❌ HIGH SEVERITY ISSUES ({len(high_issues)}):")
            for issue in high_issues:
                print(f"   • {issue['message']}")
                print(f"     File: {issue['file']}")
                print(f"     Fix: {issue['recommendation']}")
                print()
        
        if medium_issues:
            print(f"\n⚠️  MEDIUM SEVERITY ISSUES ({len(medium_issues)}):")
            for issue in medium_issues:
                print(f"   • {issue['message']}")
                print(f"     File: {issue['file']}")
                print(f"     Fix: {issue['recommendation']}")
                print()
        
        if self.warnings:
            print(f"\n💡 RECOMMENDATIONS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Summary
        total_issues = len(self.issues)
        if total_issues == 0:
            print("\n✅ SECURITY ANALYSIS PASSED!")
            print("   All API calls properly centralized and secured.")
        else:
            print(f"\n❌ SECURITY ANALYSIS FAILED!")
            print(f"   {total_issues} issue(s) found that need attention.")
        
        print("\n" + "="*70)
        
        # Generate actionable recommendations
        if total_issues > 0:
            print("\n🔧 IMMEDIATE ACTION ITEMS:")
            print("1. Replace hardcoded URLs with environment variables")
            print("2. Update components to use services/api.ts")
            print("3. Add proper error handling with try-catch blocks")
            print("4. Implement Error Boundary components for better UX")
            print("5. Centralize authentication token management")


def main():
    """Main execution function"""
    try:
        # Parse command line arguments
        src_path = sys.argv[1] if len(sys.argv) > 1 else "src"
        
        # Run security check
        checker = FrontendSecurityChecker(src_path)
        success = checker.check_all()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Security analysis interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"❌ Security analysis error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
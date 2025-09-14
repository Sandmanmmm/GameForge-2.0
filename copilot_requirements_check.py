"""
Copilot Requirements Security Check
Flags unpinned packages and broad version ranges
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict


def analyze_requirements_security(file_path: str) -> Dict:
    """Analyze requirements.txt for unpinned packages and broad ranges."""
    
    issues = []
    unpinned_packages = []
    broad_ranges = []
    duplicates = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        seen_packages = {}
        
        for line_num, line in enumerate(lines, 1):
            original_line = line.strip()
            
            # Skip comments and empty lines
            if not original_line or original_line.startswith('#') or original_line.startswith('-'):
                continue
            
            # Extract package name (handle extras like uvicorn[standard])
            package_spec = original_line.split('==')[0].split('>=')[0].split('>')[0].split('~=')[0]
            package_name = package_spec.split('[')[0].strip()
            
            # Check for duplicates
            if package_name.lower() in seen_packages:
                duplicates.append({
                    'package': package_name,
                    'lines': [seen_packages[package_name.lower()], line_num],
                    'issue': f"Duplicate package '{package_name}' on lines {seen_packages[package_name.lower()]} and {line_num}"
                })
            else:
                seen_packages[package_name.lower()] = line_num
            
            # Check for unpinned versions (using >=, >, ~=, ^)
            if '>=' in original_line or '>' in original_line and '==' not in original_line:
                unpinned_packages.append({
                    'package': package_name,
                    'line': line_num,
                    'current': original_line,
                    'issue': f"Line {line_num}: Unpinned version for '{package_name}' - uses '>=' or '>'"
                })
            
            # Check for compatible release operator
            if '~=' in original_line:
                broad_ranges.append({
                    'package': package_name,
                    'line': line_num,
                    'current': original_line,
                    'issue': f"Line {line_num}: Compatible release '~=' for '{package_name}' allows minor version updates"
                })
            
            # Check for wildcard versions
            if '.x' in original_line or '.*' in original_line:
                broad_ranges.append({
                    'package': package_name,
                    'line': line_num,
                    'current': original_line,
                    'issue': f"Line {line_num}: Wildcard version for '{package_name}' - use exact version"
                })
            
            # Check for version ranges
            if ',' in original_line and ('>' in original_line or '<' in original_line):
                broad_ranges.append({
                    'package': package_name,
                    'line': line_num,
                    'current': original_line,
                    'issue': f"Line {line_num}: Version range for '{package_name}' - use exact version"
                })
    
    except FileNotFoundError:
        return {
            'status': 'ERROR',
            'message': f"File not found: {file_path}",
            'total_issues': 1
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f"Error analyzing file: {e}",
            'total_issues': 1
        }
    
    # Calculate security score
    total_issues = len(unpinned_packages) + len(broad_ranges) + len(duplicates)
    
    if total_issues == 0:
        status = "SECURE"
        score = 10.0
    elif total_issues <= 5:
        status = "GOOD"
        score = 8.0
    elif total_issues <= 15:
        status = "ACCEPTABLE"
        score = 6.0
    else:
        status = "POOR"
        score = 3.0
    
    return {
        'status': status,
        'score': score,
        'total_issues': total_issues,
        'unpinned_packages': unpinned_packages,
        'broad_ranges': broad_ranges,
        'duplicates': duplicates,
        'recommendations': generate_recommendations(unpinned_packages, broad_ranges, duplicates)
    }


def generate_recommendations(unpinned, broad_ranges, duplicates):
    """Generate security recommendations."""
    recommendations = []
    
    if unpinned:
        recommendations.append(f"🚨 Pin {len(unpinned)} unpinned packages to exact versions")
        recommendations.append("   Replace '>=' with '==' for reproducible builds")
    
    if broad_ranges:
        recommendations.append(f"⚠️ Fix {len(broad_ranges)} broad version ranges")
        recommendations.append("   Use exact versions instead of '~=' or wildcards")
    
    if duplicates:
        recommendations.append(f"🔄 Remove {len(duplicates)} duplicate package declarations")
    
    if not unpinned and not broad_ranges and not duplicates:
        recommendations.append("✅ All packages are properly pinned")
        recommendations.append("✅ No security issues found in version specifications")
    else:
        recommendations.extend([
            "📌 Pin all dependencies to specific versions",
            "🔒 Use exact version matching (==) for production stability",
            "🧪 Test dependency updates in staging before production",
            "📝 Document version update procedures"
        ])
    
    return recommendations


def main():
    """Run Copilot requirements security check."""
    print("🔍 Copilot Requirements Security Check")
    print("=" * 50)
    print("Flagging unpinned packages and broad ranges...")
    
    # Check original requirements.txt
    original_file = "requirements.txt"
    print(f"\n📄 Analyzing: {original_file}")
    
    original_analysis = analyze_requirements_security(original_file)
    
    print(f"\n📊 ORIGINAL REQUIREMENTS ANALYSIS")
    print(f"Status: {original_analysis['status']}")
    print(f"Security Score: {original_analysis.get('score', 0):.1f}/10.0")
    print(f"Total Issues: {original_analysis['total_issues']}")
    
    if original_analysis.get('unpinned_packages'):
        print(f"\n🚨 UNPINNED PACKAGES ({len(original_analysis['unpinned_packages'])})")
        for pkg in original_analysis['unpinned_packages'][:10]:  # Show first 10
            print(f"   • {pkg['issue']}")
            print(f"     Current: {pkg['current']}")
        
        if len(original_analysis['unpinned_packages']) > 10:
            remaining = len(original_analysis['unpinned_packages']) - 10
            print(f"   ... and {remaining} more unpinned packages")
    
    if original_analysis.get('broad_ranges'):
        print(f"\n⚠️ BROAD VERSION RANGES ({len(original_analysis['broad_ranges'])})")
        for pkg in original_analysis['broad_ranges']:
            print(f"   • {pkg['issue']}")
            print(f"     Current: {pkg['current']}")
    
    if original_analysis.get('duplicates'):
        print(f"\n🔄 DUPLICATE PACKAGES ({len(original_analysis['duplicates'])})")
        for pkg in original_analysis['duplicates']:
            print(f"   • {pkg['issue']}")
    
    # Check fixed requirements if it exists
    fixed_file = "requirements_pinned.txt"
    if Path(fixed_file).exists():
        print(f"\n📄 Analyzing Fixed Version: {fixed_file}")
        
        fixed_analysis = analyze_requirements_security(fixed_file)
        
        print(f"\n📊 FIXED REQUIREMENTS ANALYSIS")
        print(f"Status: {fixed_analysis['status']}")
        print(f"Security Score: {fixed_analysis.get('score', 0):.1f}/10.0")
        print(f"Total Issues: {fixed_analysis['total_issues']}")
        
        # Show improvement
        if original_analysis.get('total_issues', 0) > fixed_analysis.get('total_issues', 0):
            improvement = original_analysis['total_issues'] - fixed_analysis['total_issues']
            print(f"✅ Improvement: Fixed {improvement} issues")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in original_analysis.get('recommendations', []):
        print(f"   {rec}")
    
    # Final verdict
    if original_analysis['total_issues'] == 0:
        print(f"\n✅ COPILOT CHECK PASSED: No unpinned packages or broad ranges")
    else:
        print(f"\n❌ COPILOT CHECK FAILED: Found {original_analysis['total_issues']} version issues")
        print(f"🔧 Use requirements_pinned.txt for fixed versions")


if __name__ == "__main__":
    main()
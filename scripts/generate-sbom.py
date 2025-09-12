#!/usr/bin/env python3
"""
GameForge AI SBOM (Software Bill of Materials) Generator
Comprehensive component inventory for supply chain security
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "sbom_generator", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class SBOMGenerator:
    """Software Bill of Materials generator for GameForge AI"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.output_dir = self.project_root / "sbom"
        self.output_dir.mkdir(exist_ok=True)
        
        # SBOM metadata
        self.sbom_metadata = {
            "component": "GameForge AI Platform",
            "version": self._get_version(),
            "supplier": "GameForge AI",
            "timestamp": datetime.now().isoformat(),
            "tools": ["syft", "cyclonedx", "spdx"],
            "formats": ["spdx-json", "cyclonedx-json", "cyclonedx-xml"]
        }
    
    def _get_version(self) -> str:
        """Get version from git or environment"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return os.getenv("VERSION", "dev")
    
    def install_tools(self) -> bool:
        """Install SBOM generation tools"""
        try:
            logger.info("🔧 Installing SBOM generation tools...")
            
            # Install Syft
            logger.info("Installing Syft...")
            subprocess.run([
                "curl", "-sSfL", 
                "https://raw.githubusercontent.com/anchore/syft/main/install.sh"
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            subprocess.run([
                "sh", "-s", "--", "-b", "/usr/local/bin"
            ], check=True, input=subprocess.run([
                "curl", "-sSfL", 
                "https://raw.githubusercontent.com/anchore/syft/main/install.sh"
            ], capture_output=True).stdout)
            
            # Verify installation
            result = subprocess.run(
                ["syft", "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Syft installed: {result.stdout.strip()}")
                return True
            else:
                logger.error("❌ Syft installation failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Tool installation failed: {e}")
            return False
    
    def generate_filesystem_sbom(self) -> Dict[str, str]:
        """Generate SBOM for filesystem/source code"""
        logger.info("📋 Generating filesystem SBOM...")
        
        sbom_files = {}
        
        try:
            # SPDX JSON format
            spdx_file = self.output_dir / "gameforge-filesystem.spdx.json"
            subprocess.run([
                "syft", str(self.project_root),
                "--output", "spdx-json",
                "--file", str(spdx_file)
            ], check=True)
            sbom_files["spdx-json"] = str(spdx_file)
            
            # CycloneDX JSON format
            cyclonedx_file = self.output_dir / "gameforge-filesystem.cyclonedx.json"
            subprocess.run([
                "syft", str(self.project_root),
                "--output", "cyclonedx-json",
                "--file", str(cyclonedx_file)
            ], check=True)
            sbom_files["cyclonedx-json"] = str(cyclonedx_file)
            
            # CycloneDX XML format
            cyclonedx_xml_file = self.output_dir / "gameforge-filesystem.cyclonedx.xml"
            subprocess.run([
                "syft", str(self.project_root),
                "--output", "cyclonedx-xml",
                "--file", str(cyclonedx_xml_file)
            ], check=True)
            sbom_files["cyclonedx-xml"] = str(cyclonedx_xml_file)
            
            # Human-readable table format
            table_file = self.output_dir / "gameforge-filesystem.txt"
            subprocess.run([
                "syft", str(self.project_root),
                "--output", "table",
                "--file", str(table_file)
            ], check=True)
            sbom_files["table"] = str(table_file)
            
            logger.info("✅ Filesystem SBOM generated")
            return sbom_files
            
        except Exception as e:
            logger.error(f"❌ Filesystem SBOM generation failed: {e}")
            return {}
    
    def generate_container_sbom(self, image_name: str) -> Dict[str, str]:
        """Generate SBOM for container image"""
        logger.info(f"📋 Generating container SBOM for: {image_name}")
        
        sbom_files = {}
        
        try:
            # SPDX JSON format
            spdx_file = self.output_dir / "gameforge-container.spdx.json"
            subprocess.run([
                "syft", image_name,
                "--output", "spdx-json",
                "--file", str(spdx_file)
            ], check=True)
            sbom_files["spdx-json"] = str(spdx_file)
            
            # CycloneDX JSON format
            cyclonedx_file = self.output_dir / "gameforge-container.cyclonedx.json"
            subprocess.run([
                "syft", image_name,
                "--output", "cyclonedx-json",
                "--file", str(cyclonedx_file)
            ], check=True)
            sbom_files["cyclonedx-json"] = str(cyclonedx_file)
            
            # CycloneDX XML format
            cyclonedx_xml_file = self.output_dir / "gameforge-container.cyclonedx.xml"
            subprocess.run([
                "syft", image_name,
                "--output", "cyclonedx-xml",
                "--file", str(cyclonedx_xml_file)
            ], check=True)
            sbom_files["cyclonedx-xml"] = str(cyclonedx_xml_file)
            
            # Human-readable table format
            table_file = self.output_dir / "gameforge-container.txt"
            subprocess.run([
                "syft", image_name,
                "--output", "table",
                "--file", str(table_file)
            ], check=True)
            sbom_files["table"] = str(table_file)
            
            logger.info("✅ Container SBOM generated")
            return sbom_files
            
        except Exception as e:
            logger.error(f"❌ Container SBOM generation failed: {e}")
            return {}
    
    def generate_python_dependencies_sbom(self) -> Dict[str, Any]:
        """Generate detailed Python dependencies SBOM"""
        logger.info("🐍 Analyzing Python dependencies...")
        
        try:
            # Get pip list in JSON format
            result = subprocess.run([
                "pip", "list", "--format=json"
            ], capture_output=True, text=True, check=True)
            
            pip_packages = json.loads(result.stdout)
            
            # Get pip show details for each package
            detailed_packages = []
            for package in pip_packages:
                try:
                    show_result = subprocess.run([
                        "pip", "show", package["name"]
                    ], capture_output=True, text=True, check=True)
                    
                    package_details = {"name": package["name"], "version": package["version"]}
                    
                    # Parse pip show output
                    for line in show_result.stdout.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip().lower().replace("-", "_")
                            value = value.strip()
                            if key in ["author", "license", "home_page", "summary"]:
                                package_details[key] = value
                    
                    detailed_packages.append(package_details)
                    
                except Exception:
                    detailed_packages.append(package)
            
            # Save Python SBOM
            python_sbom = {
                "metadata": self.sbom_metadata,
                "python_environment": {
                    "python_version": sys.version,
                    "pip_version": subprocess.run(
                        ["pip", "--version"], 
                        capture_output=True, text=True
                    ).stdout.strip()
                },
                "packages": detailed_packages,
                "total_packages": len(detailed_packages)
            }
            
            python_sbom_file = self.output_dir / "gameforge-python-deps.json"
            with open(python_sbom_file, 'w') as f:
                json.dump(python_sbom, f, indent=2)
            
            logger.info(f"✅ Python dependencies SBOM: {len(detailed_packages)} packages")
            return python_sbom
            
        except Exception as e:
            logger.error(f"❌ Python dependencies analysis failed: {e}")
            return {}
    
    def analyze_licenses(self, sbom_file: str) -> Dict[str, Any]:
        """Analyze licenses from SBOM data"""
        logger.info("📄 Analyzing software licenses...")
        
        try:
            with open(sbom_file, 'r') as f:
                sbom_data = json.load(f)
            
            licenses = {}
            components_without_license = []
            
            # Extract license information (format varies by SBOM type)
            if "packages" in sbom_data:  # SPDX format
                for package in sbom_data["packages"]:
                    license_info = package.get("licenseConcluded", "NOASSERTION")
                    if license_info == "NOASSERTION":
                        components_without_license.append(package.get("name", "unknown"))
                    else:
                        licenses[license_info] = licenses.get(license_info, 0) + 1
            
            elif "components" in sbom_data:  # CycloneDX format
                for component in sbom_data["components"]:
                    license_info = component.get("licenses", [])
                    if not license_info:
                        components_without_license.append(component.get("name", "unknown"))
                    else:
                        for license_item in license_info:
                            license_name = license_item.get("license", {}).get("name", "unknown")
                            licenses[license_name] = licenses.get(license_name, 0) + 1
            
            license_analysis = {
                "total_unique_licenses": len(licenses),
                "license_distribution": licenses,
                "components_without_license": components_without_license,
                "license_risk_assessment": self._assess_license_risk(licenses)
            }
            
            # Save license analysis
            license_file = self.output_dir / "gameforge-license-analysis.json"
            with open(license_file, 'w') as f:
                json.dump(license_analysis, f, indent=2)
            
            logger.info(f"✅ License analysis: {len(licenses)} unique licenses")
            return license_analysis
            
        except Exception as e:
            logger.error(f"❌ License analysis failed: {e}")
            return {}
    
    def _assess_license_risk(self, licenses: Dict[str, int]) -> Dict[str, List[str]]:
        """Assess license risk levels"""
        risk_categories = {
            "permissive": ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC"],
            "weak_copyleft": ["LGPL-2.1", "LGPL-3.0", "MPL-2.0"],
            "strong_copyleft": ["GPL-2.0", "GPL-3.0", "AGPL-3.0"],
            "commercial": ["Commercial", "Proprietary"],
            "unknown": ["NOASSERTION", "unknown", ""]
        }
        
        assessment = {category: [] for category in risk_categories}
        
        for license_name in licenses:
            categorized = False
            for category, license_list in risk_categories.items():
                if any(known_license in license_name for known_license in license_list):
                    assessment[category].append(license_name)
                    categorized = True
                    break
            
            if not categorized:
                assessment["unknown"].append(license_name)
        
        return assessment
    
    def generate_comprehensive_report(self, 
                                    filesystem_sboms: Dict[str, str],
                                    container_sboms: Dict[str, str],
                                    python_sbom: Dict[str, Any],
                                    license_analysis: Dict[str, Any]) -> str:
        """Generate comprehensive SBOM report"""
        logger.info("📊 Generating comprehensive SBOM report...")
        
        try:
            report = {
                "metadata": self.sbom_metadata,
                "summary": {
                    "total_sbom_files": len(filesystem_sboms) + len(container_sboms) + 1,
                    "formats_generated": list(set(list(filesystem_sboms.keys()) + list(container_sboms.keys()))),
                    "python_packages": python_sbom.get("total_packages", 0),
                    "unique_licenses": license_analysis.get("total_unique_licenses", 0)
                },
                "files": {
                    "filesystem_sboms": filesystem_sboms,
                    "container_sboms": container_sboms,
                    "python_dependencies": "gameforge-python-deps.json",
                    "license_analysis": "gameforge-license-analysis.json"
                },
                "license_summary": license_analysis.get("license_distribution", {}),
                "security_considerations": {
                    "components_without_license": len(license_analysis.get("components_without_license", [])),
                    "high_risk_licenses": license_analysis.get("license_risk_assessment", {}).get("strong_copyleft", []),
                    "unknown_licenses": license_analysis.get("license_risk_assessment", {}).get("unknown", [])
                },
                "recommendations": self._generate_recommendations(license_analysis)
            }
            
            report_file = self.output_dir / "gameforge-sbom-report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Generate human-readable summary
            self._generate_human_readable_report(report)
            
            logger.info(f"✅ Comprehensive SBOM report generated: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return ""
    
    def _generate_recommendations(self, license_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on SBOM analysis"""
        recommendations = []
        
        # License recommendations
        risk_assessment = license_analysis.get("license_risk_assessment", {})
        
        if risk_assessment.get("strong_copyleft"):
            recommendations.append(
                "Review strong copyleft licenses (GPL) for compliance requirements"
            )
        
        if risk_assessment.get("unknown"):
            recommendations.append(
                "Investigate components with unknown or unspecified licenses"
            )
        
        if license_analysis.get("components_without_license"):
            recommendations.append(
                f"Identify licenses for {len(license_analysis['components_without_license'])} unlicensed components"
            )
        
        # General recommendations
        recommendations.extend([
            "Regularly update SBOM as dependencies change",
            "Implement license compliance monitoring in CI/CD",
            "Consider using automated license scanning tools",
            "Maintain inventory of approved licenses for the organization"
        ])
        
        return recommendations
    
    def _generate_human_readable_report(self, report_data: Dict[str, Any]):
        """Generate human-readable markdown report"""
        markdown_content = f"""# GameForge AI - Software Bill of Materials Report

**Generated:** {report_data['metadata']['timestamp']}
**Version:** {report_data['metadata']['version']}

## 📊 Summary

- **Total SBOM Files:** {report_data['summary']['total_sbom_files']}
- **Python Packages:** {report_data['summary']['python_packages']}
- **Unique Licenses:** {report_data['summary']['unique_licenses']}
- **Formats Generated:** {', '.join(report_data['summary']['formats_generated'])}

## 📄 License Distribution

"""
        
        for license_name, count in report_data['license_summary'].items():
            markdown_content += f"- **{license_name}:** {count} components\n"
        
        markdown_content += f"""

## 🚨 Security Considerations

- **Components without license:** {report_data['security_considerations']['components_without_license']}
- **High-risk licenses:** {len(report_data['security_considerations']['high_risk_licenses'])}
- **Unknown licenses:** {len(report_data['security_considerations']['unknown_licenses'])}

## 📋 Recommendations

"""
        
        for rec in report_data['recommendations']:
            markdown_content += f"- {rec}\n"
        
        markdown_content += f"""

## 📁 Generated Files

### Filesystem SBOMs
"""
        for format_type, file_path in report_data['files']['filesystem_sboms'].items():
            markdown_content += f"- **{format_type.upper()}:** `{Path(file_path).name}`\n"
        
        if report_data['files']['container_sboms']:
            markdown_content += "\n### Container SBOMs\n"
            for format_type, file_path in report_data['files']['container_sboms'].items():
                markdown_content += f"- **{format_type.upper()}:** `{Path(file_path).name}`\n"
        
        markdown_content += f"""

### Analysis Files
- **Python Dependencies:** `{report_data['files']['python_dependencies']}`
- **License Analysis:** `{report_data['files']['license_analysis']}`

---
*This SBOM was generated using Syft and custom analysis tools for supply chain security.*
"""
        
        markdown_file = self.output_dir / "gameforge-sbom-report.md"
        with open(markdown_file, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"✅ Human-readable report: {markdown_file}")

async def main():
    """Main SBOM generation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge AI SBOM Generator')
    parser.add_argument('--install-tools', action='store_true', help='Install SBOM generation tools')
    parser.add_argument('--filesystem', action='store_true', help='Generate filesystem SBOM')
    parser.add_argument('--container', help='Generate container SBOM for specified image')
    parser.add_argument('--python-deps', action='store_true', help='Analyze Python dependencies')
    parser.add_argument('--all', action='store_true', help='Generate all SBOMs and reports')
    
    args = parser.parse_args()
    
    generator = SBOMGenerator()
    
    try:
        if args.install_tools or args.all:
            if not generator.install_tools():
                sys.exit(1)
        
        filesystem_sboms = {}
        container_sboms = {}
        python_sbom = {}
        license_analysis = {}
        
        if args.filesystem or args.all:
            filesystem_sboms = generator.generate_filesystem_sbom()
        
        if args.container or args.all:
            image_name = args.container or "gameforge/ai-platform:latest"
            container_sboms = generator.generate_container_sbom(image_name)
        
        if args.python_deps or args.all:
            python_sbom = generator.generate_python_dependencies_sbom()
        
        # Generate license analysis if we have SBOM data
        if filesystem_sboms.get("spdx-json"):
            license_analysis = generator.analyze_licenses(filesystem_sboms["spdx-json"])
        elif container_sboms.get("spdx-json"):
            license_analysis = generator.analyze_licenses(container_sboms["spdx-json"])
        
        if args.all or any([filesystem_sboms, container_sboms, python_sbom]):
            generator.generate_comprehensive_report(
                filesystem_sboms, container_sboms, python_sbom, license_analysis
            )
        
        logger.info("🎉 SBOM generation completed successfully")
        
    except Exception as e:
        logger.error(f"❌ SBOM generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
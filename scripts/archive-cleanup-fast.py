#!/usr/bin/env python3
"""
GameForge Repository Archive Strategy - Fast Version
Quickly analyzes and moves legacy files to archive/ branch
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Set
import time

class FastRepositoryArchiver:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.current_branch = self._get_current_branch()
        
        # Top-level items to archive (specific files we know exist)
        self.top_level_archive_items = [
            # Legacy scripts and configs
            "access-security-dashboard.ps1", "analyze-docker-security.sh",
            "auth_middleware.py", "backend_gpu_integration.py", "backup-production.ps1",
            "backup-simple.ps1", "build-phase2-clean.ps1", "build-phase2-phase4-integration.ps1",
            "build-phase2-simple.ps1", "build-phase2.bat", "build-phase2.ps1", "build-phase2.sh",
            "build-phase4-complete.ps1", "build-reproducible.sh", "build.sh",
            "check-oauth-config.js", "check-ports-simple.ps1", "check-ports.ps1",
            "cicd-secret-rotation.ps1", "configure-security-environment.ps1", "configure-security.ps1",
            "custom_sdxl_pipeline.py", "database_setup.sql", "debug-lsm-building.sh",
            
            # Legacy Dockerfiles
            "gameforge-ai-lightweight.Dockerfile", "gameforge-ai-rtx4090.Dockerfile",
            "gameforge-ai.Dockerfile", "gameforge-test.Dockerfile",
            
            # Various Python files
            "gameforge_app_metrics.py", "gameforge_metrics_app.py", "gameforge_production_server.py",
            "gameforge_rtx4090_optimized.py", "gameforge_rtx4090_server.py", "install_dependencies.py",
            "install_dependencies_windows.bat", "migrate-to-cloud.ps1", "model_externalization.py",
            "monitor_deployment.py", "optimized_sdxl_service.py", "PRODUCTION_STATUS.py",
            "rate_limit_middleware.py", "security_integration.py", "user_management.py",
            "verify_deployment.py",
            
            # Config files
            "nginx-hardened.conf", "nginx-json-logging.conf", "nginx-proxy-params.conf",
            "filebeat.yml", "external-storage-config.yaml", "tailwind.config.js",
            "tsconfig.json", "vite.config.ts", "test-build.cmd", "test-sdxl-integration.js",
            "test_e2e_pipeline.py", "oauth-setup-assistant.html", "oauth-test.js",
            "index.html", "kind.exe", "GameForge.code-workspace",
            
            # Jupyter notebooks
            "GameForge_VSCode_Jupyter_Integration.ipynb", "vast_deployment_notebook.ipynb",
            
            # Various requirements files (keep main requirements.txt)
            "requirements-gpu.txt", "requirements-lightweight.txt", "requirements-locked-demo.txt",
            "requirements-minimal.txt", "requirements-model-management.txt", "requirements-production.txt",
            "requirements-simple.in", "requirements-vastai.txt", "requirements.in"
        ]
        
        # Directories to archive completely
        self.directories_to_archive = [
            "audit", "backend", "backup", "backups", "backup_20250912_004935", "backup_local_changes",
            "certs", "config", "core", "data", "database", "deployment", "dist", "elasticsearch",
            "email_templates", "filebeat", "grafana", "helm", "kibana", "logs", "logstash",
            "migration", "migrations", "monitoring", "nginx", "ops", "phase1-reports",
            "phase5-test-reports", "prometheus", "redis", "reports", "sbom", "scaling-configs",
            "sdxl_pipeline", "secrets", "security", "security-reports", "security-scans",
            "services", "ssl", "state", "vault", "volumes"
        ]

    def _get_current_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, cwd=self.repo_path, timeout=10)
            return result.stdout.strip()
        except:
            return "main"

    def quick_analysis(self) -> Dict:
        """Quick analysis of what would be archived"""
        print("🔍 Running quick repository analysis...")
        
        # Count top-level items
        try:
            top_level_items = list(self.repo_path.iterdir())
            all_items = [item.name for item in top_level_items]
        except:
            print("❌ Error reading directory")
            return {}
        
        # Categorize items
        files_to_archive = []
        dirs_to_archive = []
        items_to_keep = []
        
        for item_name in all_items:
            if item_name.startswith('.'):
                continue
                
            if item_name in self.top_level_archive_items:
                files_to_archive.append(item_name)
            elif item_name in self.directories_to_archive:
                dirs_to_archive.append(item_name)
            else:
                items_to_keep.append(item_name)
        
        # Calculate rough sizes (without traversing huge directories)
        total_items = len(all_items)
        archive_items = len(files_to_archive) + len(dirs_to_archive)
        keep_items = len(items_to_keep)
        
        analysis = {
            "total_top_level_items": total_items,
            "items_to_archive": archive_items,
            "items_to_keep": keep_items,
            "files_to_archive": files_to_archive[:10],  # Show first 10
            "dirs_to_archive": dirs_to_archive[:10],    # Show first 10
            "items_to_keep": items_to_keep,
            "reduction_percent": round((archive_items / total_items) * 100, 1) if total_items > 0 else 0
        }
        
        return analysis

    def show_analysis(self):
        """Show what would be archived"""
        analysis = self.quick_analysis()
        
        if not analysis:
            return
            
        print(f"\n📊 Quick Repository Analysis:")
        print(f"  Total top-level items: {analysis['total_top_level_items']}")
        print(f"  Items to archive: {analysis['items_to_archive']}")
        print(f"  Items to keep: {analysis['items_to_keep']}")
        print(f"  Cleanup reduction: {analysis['reduction_percent']}%")
        
        print(f"\n📁 Sample files to archive:")
        for file in analysis['files_to_archive']:
            print(f"    {file}")
        if len(self.top_level_archive_items) > 10:
            print(f"    ... and {len(self.top_level_archive_items) - 10} more files")
            
        print(f"\n📂 Directories to archive:")
        for dir_name in analysis['dirs_to_archive']:
            print(f"    {dir_name}/")
        if len(self.directories_to_archive) > 10:
            print(f"    ... and {len(self.directories_to_archive) - 10} more directories")
            
        print(f"\n✅ Items to keep in main branch:")
        for item in analysis['items_to_keep']:
            print(f"    {item}")

    def create_organized_structure(self):
        """Create clean directory structure"""
        print("📁 Creating organized directory structure...")
        
        structure_dirs = [
            "src", "src/backend", "src/frontend", "src/ai",
            "docker", "docker/base", "docker/services",
            "k8s", "k8s/base", "k8s/environments", 
            "ci", "scripts", "docs", "tests", "config"
        ]
        
        for dir_path in structure_dirs:
            full_path = self.repo_path / dir_path
            full_path.mkdir(exist_ok=True)
            
            # Create README if it doesn't exist
            readme_path = full_path / "README.md"
            if not readme_path.exists():
                with open(readme_path, 'w') as f:
                    f.write(f"# {dir_path}\n\nDirectory for {dir_path.split('/')[-1]} components.\n")
        
        print("✅ Organized structure created")

    def simulate_cleanup(self):
        """Simulate the cleanup without actually moving files"""
        print("🧪 Simulating cleanup process...")
        
        analysis = self.quick_analysis()
        if not analysis:
            return False
            
        print(f"\n🔄 Cleanup simulation:")
        print(f"  Would archive {analysis['items_to_archive']} top-level items")
        print(f"  Would keep {analysis['items_to_keep']} organized items")
        print(f"  Repository cleanup: {analysis['reduction_percent']}% reduction")
        
        print(f"\n📋 Recommended next steps:")
        print(f"  1. Review the items to be archived above")
        print(f"  2. Run: python scripts/archive-cleanup-fast.py --create-structure")
        print(f"  3. Manually organize remaining files into src/, docker/, k8s/, etc.")
        print(f"  4. Run guardrails to verify: .\\scripts\\guardrails-hardened.ps1")
        
        return True

    def execute_archival(self, dry_run=True):
        """Execute the actual archival process"""
        print("🗂️ Executing repository archival process...")
        
        analysis = self.quick_analysis()
        if not analysis:
            print("❌ Could not analyze repository")
            return False
        
        print(f"\n📊 Archival Summary:")
        print(f"  Items to archive: {analysis['items_to_archive']}")
        print(f"  Repository cleanup: {analysis['reduction_percent']}%")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would archive these items:")
            # Show files to archive
            print(f"\n📄 Files to archive:")
            for item in self.top_level_archive_items:
                if (self.repo_path / item).exists():
                    print(f"    {item}")
            
            print(f"\n📁 Directories to archive:")
            for item in self.directories_to_archive:
                if (self.repo_path / item).exists():
                    print(f"    {item}/")
            
            print(f"\n💡 To execute archival: python scripts/archive-cleanup-fast.py --execute")
            return True
        
        # Confirm before proceeding
        response = input(f"\n⚠️  This will archive {analysis['items_to_archive']} items to a new branch. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Archival cancelled")
            return False
        
        try:
            # Get current branch and commit state
            print("🔍 Checking repository state...")
            
            # Check for uncommitted changes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.stdout.strip():
                print("⚠️  Uncommitted changes detected. Please commit or stash changes first.")
                print("Run: git add . && git commit -m 'Pre-archival commit'")
                return False
            
            # Create archive branch
            branch_name = f"archive/cleanup-{int(time.time())}"
            print(f"🌿 Creating archive branch: {branch_name}")
            
            result = subprocess.run(['git', 'checkout', '-b', branch_name], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            if result.returncode != 0:
                print(f"❌ Failed to create branch: {result.stderr}")
                return False
            
            # Create archive directory structure
            archive_base = self.repo_path / "archive"
            archive_base.mkdir(exist_ok=True)
            
            archive_dirs = {
                "legacy-scripts": "Legacy deployment and build scripts",
                "legacy-configs": "Legacy configuration files", 
                "legacy-python": "Legacy Python files",
                "legacy-dockerfiles": "Legacy Dockerfile variants",
                "legacy-notebooks": "Jupyter notebooks and development files",
                "legacy-requirements": "Various requirements files",
                "legacy-services": "Legacy service directories",
                "legacy-monitoring": "Legacy monitoring and ops directories",
                "legacy-data": "Legacy data and backup directories"
            }
            
            for dir_name, description in archive_dirs.items():
                dir_path = archive_base / dir_name
                dir_path.mkdir(exist_ok=True)
                
                # Create README in archive directory
                readme_path = dir_path / "README.md"
                with open(readme_path, 'w') as f:
                    f.write(f"# {dir_name.replace('-', ' ').title()}\n\n{description}\n\n")
                    f.write(f"Archived on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Original branch: {self.current_branch}\n\n")
            
            moved_items = []
            
            # Move files to appropriate archive directories
            file_categories = {
                "legacy-scripts": [item for item in self.top_level_archive_items if item.endswith(('.ps1', '.sh', '.bat', '.cmd'))],
                "legacy-configs": [item for item in self.top_level_archive_items if item.endswith(('.conf', '.yml', '.yaml', '.json', '.js', '.ts')) and not item.startswith('gameforge')],
                "legacy-python": [item for item in self.top_level_archive_items if item.endswith('.py')],
                "legacy-dockerfiles": [item for item in self.top_level_archive_items if 'Dockerfile' in item or item.startswith('gameforge-')],
                "legacy-notebooks": [item for item in self.top_level_archive_items if item.endswith(('.ipynb', '.html'))],
                "legacy-requirements": [item for item in self.top_level_archive_items if item.startswith('requirements-') or item.endswith('.in')],
            }
            
            # Move categorized files
            for category, files in file_categories.items():
                for file_name in files:
                    source_path = self.repo_path / file_name
                    if source_path.exists():
                        dest_path = archive_base / category / file_name
                        print(f"📦 Moving {file_name} to archive/{category}/")
                        source_path.rename(dest_path)
                        moved_items.append(f"{file_name} -> archive/{category}/")
            
            # Move miscellaneous files
            for file_name in self.top_level_archive_items:
                source_path = self.repo_path / file_name
                if source_path.exists():
                    # Determine category based on extension or content
                    if file_name.endswith(('.exe', '.code-workspace')):
                        category = "legacy-scripts"
                    else:
                        category = "legacy-configs"
                    
                    dest_path = archive_base / category / file_name
                    if not dest_path.exists():  # Don't move if already moved
                        print(f"📦 Moving {file_name} to archive/{category}/")
                        source_path.rename(dest_path)
                        moved_items.append(f"{file_name} -> archive/{category}/")
            
            # Move directories
            dir_categories = {
                "legacy-services": ["backend", "core", "services", "email_templates"],
                "legacy-monitoring": ["monitoring", "prometheus", "grafana", "elasticsearch", "kibana", "logstash", "filebeat"],
                "legacy-data": ["backup", "backups", "backup_20250912_004935", "backup_local_changes", "data", "logs", "reports", "phase1-reports", "phase5-test-reports"],
                "legacy-configs": ["config", "certs", "ssl", "secrets", "vault", "nginx", "scaling-configs"],
                "legacy-services": ["audit", "deployment", "migration", "migrations", "ops", "security", "security-reports", "security-scans", "sbom", "state", "volumes", "helm", "redis", "database", "dist", "sdxl_pipeline"]
            }
            
            for category, dirs in dir_categories.items():
                for dir_name in dirs:
                    if dir_name in self.directories_to_archive:
                        source_path = self.repo_path / dir_name
                        if source_path.exists() and source_path.is_dir():
                            dest_path = archive_base / category / dir_name
                            print(f"📁 Moving {dir_name}/ to archive/{category}/")
                            source_path.rename(dest_path)
                            moved_items.append(f"{dir_name}/ -> archive/{category}/")
            
            # Create archive summary
            summary_path = archive_base / "ARCHIVE_SUMMARY.md"
            with open(summary_path, 'w') as f:
                f.write("# GameForge Repository Archive Summary\n\n")
                f.write(f"**Archived on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Original branch:** {self.current_branch}\n")
                f.write(f"**Archive branch:** {branch_name}\n")
                f.write(f"**Items archived:** {len(moved_items)}\n\n")
                f.write("## Archived Items\n\n")
                for item in moved_items:
                    f.write(f"- {item}\n")
                f.write(f"\n## Purpose\n\n")
                f.write("This archive was created to clean up the main repository structure ")
                f.write("while preserving all legacy files and their git history. ")
                f.write("The main branch now maintains a clean, organized structure suitable for production.\n\n")
                f.write("## Accessing Archived Files\n\n")
                f.write(f"To access archived files:\n")
                f.write(f"```bash\n")
                f.write(f"git checkout {branch_name}\n")
                f.write(f"# Files are in archive/ directory\n")
                f.write(f"```\n\n")
                f.write(f"To restore specific files:\n")
                f.write(f"```bash\n")
                f.write(f"git checkout {branch_name} -- archive/category/filename\n")
                f.write(f"```\n")
            
            # Commit archive branch
            print("💾 Committing archive branch...")
            subprocess.run(['git', 'add', '.'], cwd=self.repo_path)
            subprocess.run(['git', 'commit', '-m', f'Archive legacy files - repository cleanup'], cwd=self.repo_path)
            
            # Switch back to original branch
            print(f"🔄 Switching back to {self.current_branch} branch...")
            subprocess.run(['git', 'checkout', self.current_branch], cwd=self.repo_path)
            
            # Remove empty directories that might be left
            self._remove_empty_directories()
            
            # Commit cleanup in main branch
            print("🧹 Committing cleanup in main branch...")
            subprocess.run(['git', 'add', '-A'], cwd=self.repo_path)
            subprocess.run(['git', 'commit', '-m', f'Clean repository structure - archived {len(moved_items)} legacy items'], cwd=self.repo_path)
            
            print(f"\n✅ Repository archival complete!")
            print(f"   📦 Archived {len(moved_items)} items to branch: {branch_name}")
            print(f"   🧹 Main branch cleaned and organized")
            print(f"   📉 Repository structure simplified by {analysis['reduction_percent']}%")
            print(f"\n🔍 Next steps:")
            print(f"   1. Run: .\\scripts\\guardrails-hardened.ps1")
            print(f"   2. Verify repository structure is clean")
            print(f"   3. Continue with Docker image hardening")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during archival: {e}")
            # Try to return to original branch
            try:
                subprocess.run(['git', 'checkout', self.current_branch], cwd=self.repo_path)
            except:
                pass
            return False

    def _remove_empty_directories(self):
        """Remove empty directories after cleanup"""
        try:
            for root, dirs, files in os.walk(self.repo_path, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if dir_path.is_dir() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            print(f"🗑️ Removed empty directory: {dir_path.relative_to(self.repo_path)}")
                    except OSError:
                        pass  # Directory not empty or permission issue
        except Exception as e:
            print(f"⚠️ Could not remove some empty directories: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fast repository cleanup analysis')
    parser.add_argument('--analyze', action='store_true', help='Show what would be archived')
    parser.add_argument('--simulate', action='store_true', help='Simulate cleanup process')
    parser.add_argument('--create-structure', action='store_true', help='Create organized directory structure')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without doing it')
    parser.add_argument('--execute', action='store_true', help='Execute actual archival (moves files to archive branch)')
    
    args = parser.parse_args()
    
    # Initialize cleanup
    cleanup = FastRepositoryArchiver()
    
    if args.create_structure:
        cleanup.create_organized_structure()
    elif args.simulate:
        cleanup.simulate_cleanup()
    elif args.dry_run:
        cleanup.execute_archival(dry_run=True)
    elif args.execute:
        cleanup.execute_archival(dry_run=False)
    else:
        # Default to analysis
        cleanup.show_analysis()

if __name__ == '__main__':
    main()
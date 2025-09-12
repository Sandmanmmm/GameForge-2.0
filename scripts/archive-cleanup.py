#!/usr/bin/env python3
"""
GameForge Repository Archive Strategy
Moves legacy files to archive/ branch while preserving git history
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Set
import tempfile
import shutil

class RepositoryArchiver:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.current_branch = self._get_current_branch()
        
        # Files/directories to archive (move to archive/ branch)
        self.archive_targets = {
            # Legacy deployment files
            "legacy_deployment": [
                "build-*.ps1", "build-*.sh", "build-*.bat",
                "deploy-*.ps1", "deploy-*.sh", 
                "backup*.ps1", "backup*.sh",
                "*-legacy.*", "*-old.*", "*-backup.*",
                "gameforge-*.Dockerfile",  # Legacy Dockerfiles
                "test-*.cmd", "test-*.js",
                "migrate-*.ps1", "*-migration.*"
            ],
            
            # Backup directories
            "backup_data": [
                "backup*", "backups*", "backup_*",
                "phase*-reports", "*-reports",
                "security-scans", "security-reports"
            ],
            
            # Legacy configurations
            "legacy_configs": [
                "docker-compose.*.yml",  # Keep only main ones
                "requirements-*.txt",    # Consolidate these
                "*-hardened.conf", "*-json-logging.conf",
                "nginx-*.conf", "filebeat.yml",
                "external-storage-config.yaml"
            ],
            
            # Development artifacts
            "dev_artifacts": [
                "*.code-workspace", "tsconfig.json",
                "tailwind.config.js", "vite.config.ts",
                "components.json", "*.ipynb",
                "install_dependencies*", "kind.exe"
            ],
            
            # Monitoring and ops (move to archive, reorganize)
            "ops_legacy": [
                "monitoring", "prometheus", "grafana", 
                "elasticsearch", "kibana", "logstash",
                "filebeat", "audit", "ops"
            ],
            
            # Legacy services
            "legacy_services": [
                "services", "core", "migration", "migrations",
                "email_templates", "ssl", "certs", "vault",
                "volumes", "state", "scaling-configs"
            ],
            
            # Legacy Python files (move to proper structure)
            "legacy_python": [
                "*.py",  # All top-level Python files
                "auth_middleware.py", "backend_gpu_integration.py",
                "custom_sdxl_pipeline.py", "database_setup.sql",
                "gameforge_*.py", "install_dependencies.py",
                "model_externalization.py", "monitor_deployment.py",
                "optimized_sdxl_service.py", "PRODUCTION_STATUS.py",
                "rate_limit_middleware.py", "security_integration.py",
                "test_e2e_pipeline.py", "user_management.py",
                "verify_deployment.py"
            ]
        }
        
        # Files to keep in main branch (organized structure)
        self.keep_files = {
            "src/", "docker/", "k8s/", "ci/", "scripts/", "docs/", "tests/", "config/",
            "package.json", "package-lock.json", "requirements.txt", "setup.py",
            "README.md", "LICENSE", ".gitignore", ".dockerignore",
            "Dockerfile", "docker-compose.yml", "docker-compose.prod.yml", "docker-compose.dev.yml",
            ".env.example", "Makefile"
        }

    def _get_current_branch(self) -> str:
        """Get current git branch"""
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=self.repo_path)
        return result.stdout.strip()

    def _run_git_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run git command and return result"""
        return subprocess.run(['git'] + cmd, cwd=self.repo_path, 
                            capture_output=True, text=True)

    def analyze_repository(self) -> Dict[str, List[str]]:
        """Analyze repository and categorize files for archiving"""
        analysis = {
            "to_archive": [],
            "to_keep": [],
            "to_reorganize": [],
            "size_analysis": {}
        }

        # Get all files in repository
        all_files = []
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                all_files.append(rel_path)

        # Categorize files
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            
            # Check if file should be kept
            keep_file = False
            for keep_pattern in self.keep_files:
                if file_path.startswith(keep_pattern) or file_name == keep_pattern:
                    keep_file = True
                    break
            
            if keep_file:
                analysis["to_keep"].append(file_path)
                continue
                
            # Check if file should be archived
            archived = False
            for category, patterns in self.archive_targets.items():
                for pattern in patterns:
                    if self._matches_pattern(file_path, pattern):
                        analysis["to_archive"].append(file_path)
                        archived = True
                        break
                if archived:
                    break
            
            if not archived:
                analysis["to_reorganize"].append(file_path)

        # Size analysis
        total_size = 0
        archive_size = 0
        for file_path in all_files:
            try:
                size = os.path.getsize(os.path.join(self.repo_path, file_path))
                total_size += size
                if file_path in analysis["to_archive"]:
                    archive_size += size
            except OSError:
                continue
                
        analysis["size_analysis"] = {
            "total_files": len(all_files),
            "files_to_archive": len(analysis["to_archive"]),
            "files_to_keep": len(analysis["to_keep"]),
            "total_size_mb": round(total_size / (1024*1024), 2),
            "archive_size_mb": round(archive_size / (1024*1024), 2),
            "reduction_percent": round((archive_size / total_size) * 100, 1)
        }

        return analysis

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file matches archive pattern"""
        import fnmatch
        
        # Check filename
        if fnmatch.fnmatch(os.path.basename(file_path), pattern):
            return True
        
        # Check full path
        if fnmatch.fnmatch(file_path, pattern):
            return True
            
        # Check if it's a directory pattern
        if pattern.endswith('/') or not '.' in pattern:
            if file_path.startswith(pattern.rstrip('/')):
                return True
                
        return False

    def create_archive_branch(self, dry_run: bool = True) -> bool:
        """Create archive branch and move legacy files"""
        
        print(f"🔍 Analyzing repository for archival...")
        analysis = self.analyze_repository()
        
        print(f"\n📊 Repository Analysis:")
        print(f"  Total files: {analysis['size_analysis']['total_files']}")
        print(f"  Files to archive: {analysis['size_analysis']['files_to_archive']}")
        print(f"  Files to keep: {analysis['size_analysis']['files_to_keep']}")
        print(f"  Size reduction: {analysis['size_analysis']['reduction_percent']}% ({analysis['size_analysis']['archive_size_mb']} MB)")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Files that would be archived:")
            for file_path in analysis["to_archive"][:20]:  # Show first 20
                print(f"    {file_path}")
            if len(analysis["to_archive"]) > 20:
                print(f"    ... and {len(analysis['to_archive']) - 20} more files")
            return True

        # Confirm before proceeding
        response = input(f"\n⚠️  This will archive {len(analysis['to_archive'])} files. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Archive operation cancelled")
            return False

        try:
            # Create archive branch
            print(f"🌿 Creating archive branch...")
            self._run_git_command(['checkout', '-b', 'archive/legacy-cleanup'])
            
            # Create archive directory structure
            archive_dirs = [
                'archive/legacy-deployment',
                'archive/backup-data', 
                'archive/legacy-configs',
                'archive/dev-artifacts',
                'archive/ops-legacy',
                'archive/legacy-services',
                'archive/legacy-python'
            ]
            
            for dir_path in archive_dirs:
                os.makedirs(dir_path, exist_ok=True)
            
            # Move files to archive structure
            moved_files = []
            for file_path in analysis["to_archive"]:
                category = self._get_file_category(file_path)
                archive_path = f"archive/{category}/{os.path.basename(file_path)}"
                
                # Create subdirectory if needed
                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                
                # Move file
                if os.path.exists(file_path):
                    shutil.move(file_path, archive_path)
                    moved_files.append((file_path, archive_path))
            
            # Commit archive branch
            self._run_git_command(['add', '.'])
            self._run_git_command(['commit', '-m', 'Archive legacy files for repository cleanup'])
            
            # Switch back to main branch
            self._run_git_command(['checkout', self.current_branch])
            
            # Remove archived files from main branch
            for original_path, _ in moved_files:
                if os.path.exists(original_path):
                    os.remove(original_path)
            
            # Remove empty directories
            self._remove_empty_dirs()
            
            # Commit cleanup
            self._run_git_command(['add', '-A'])
            self._run_git_command(['commit', '-m', 'Clean up repository structure - archived legacy files'])
            
            print(f"✅ Repository cleanup complete!")
            print(f"   📦 Legacy files archived in branch: archive/legacy-cleanup")
            print(f"   🧹 Main branch cleaned up")
            print(f"   📉 Reduced repository size by {analysis['size_analysis']['reduction_percent']}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during archive operation: {e}")
            # Try to return to original branch
            self._run_git_command(['checkout', self.current_branch])
            return False

    def _get_file_category(self, file_path: str) -> str:
        """Determine which archive category a file belongs to"""
        for category, patterns in self.archive_targets.items():
            for pattern in patterns:
                if self._matches_pattern(file_path, pattern):
                    return category.replace('_', '-')
        return 'misc'

    def _remove_empty_dirs(self):
        """Remove empty directories after cleanup"""
        for root, dirs, files in os.walk(self.repo_path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)

    def create_new_structure(self):
        """Create organized directory structure for remaining files"""
        structure = {
            'src/': 'Application source code',
            'src/backend/': 'Backend API services',
            'src/frontend/': 'Frontend application',
            'src/ai/': 'AI/ML services',
            'docker/': 'Docker configurations',
            'docker/base/': 'Base image definitions',
            'docker/services/': 'Service-specific Dockerfiles',
            'k8s/': 'Kubernetes manifests',
            'k8s/base/': 'Base Kubernetes resources',
            'k8s/environments/': 'Environment-specific configs',
            'ci/': 'CI/CD pipeline definitions',
            'scripts/': 'Utility scripts',
            'docs/': 'Documentation',
            'tests/': 'Test files',
            'config/': 'Configuration templates'
        }
        
        print(f"📁 Creating organized directory structure...")
        for dir_path, description in structure.items():
            os.makedirs(dir_path, exist_ok=True)
            
            # Create README in each directory
            readme_path = os.path.join(dir_path, 'README.md')
            if not os.path.exists(readme_path):
                with open(readme_path, 'w') as f:
                    f.write(f"# {dir_path.rstrip('/')}\n\n{description}\n")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Archive legacy files and clean repository structure')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without making changes')
    parser.add_argument('--analyze', action='store_true', help='Only analyze repository without making changes')
    parser.add_argument('--create-structure', action='store_true', help='Create organized directory structure')
    
    args = parser.parse_args()
    
    archiver = RepositoryArchiver()
    
    if args.analyze:
        analysis = archiver.analyze_repository()
        print(json.dumps(analysis, indent=2))
    elif args.create_structure:
        archiver.create_new_structure()
        print("✅ Directory structure created")
    else:
        archiver.create_archive_branch(dry_run=args.dry_run)

if __name__ == '__main__':
    main()
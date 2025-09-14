#!/usr/bin/env python3
"""
GameForge Large File Detection Script

Copilot security check to identify binary files >20MB in git history and current tree.
Produces list and suggested moves to external storage.

Usage:
    python copilot_large_file_check.py
    
Requirements:
    - Git repository 
    - Python 3.7+
    - Git command line tools
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime


class LargeFileDetector:
    """Detect large files in Git repository"""
    
    def __init__(self, repo_path: str = ".", size_threshold_mb: int = 20):
        self.repo_path = Path(repo_path).resolve()
        self.size_threshold_bytes = size_threshold_mb * 1024 * 1024
        self.size_threshold_mb = size_threshold_mb
        
        # Binary file extensions to watch for
        self.binary_extensions = {
            # Model files
            '.safetensors', '.bin', '.pt', '.pth', '.ckpt', '.h5', '.pkl', '.pickle',
            # Media files
            '.mp4', '.avi', '.mov', '.mkv', '.wav', '.mp3', '.flac', '.ogg',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
            # Archives
            '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
            # Documents
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            # Other binaries
            '.exe', '.dll', '.so', '.dylib', '.deb', '.rpm', '.dmg', '.iso'
        }
        
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run_git_command(self, cmd: List[str]) -> str:
        """Run git command and return output"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
            return ""
        except FileNotFoundError:
            print("❌ Git command not found. Please install Git.")
            sys.exit(1)
    
    def get_large_objects_from_history(self) -> List[Dict]:
        """
        Find large objects in git history using git rev-list --objects --all
        """
        print("🔍 Scanning git history for large objects...")
        
        # Get all objects in git history
        objects_output = self.run_git_command(['git', 'rev-list', '--objects', '--all'])
        if not objects_output:
            return []
        
        large_objects = []
        object_lines = objects_output.split('\n')
        
        print(f"📊 Checking {len(object_lines)} objects...")
        
        for i, line in enumerate(object_lines):
            if not line.strip():
                continue
                
            # Show progress every 1000 objects
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(object_lines)} objects checked")
                
            parts = line.split(' ', 1)
            if len(parts) != 2:
                continue
                
            object_hash, file_path = parts
            
            # Get object size using git cat-file
            try:
                size_output = self.run_git_command(['git', 'cat-file', '-s', object_hash])
                if size_output:
                    size_bytes = int(size_output)
                    
                    if size_bytes > self.size_threshold_bytes:
                        # Check if it's a binary file
                        is_binary = self.is_likely_binary(file_path)
                        
                        large_objects.append({
                            'hash': object_hash,
                            'path': file_path,
                            'size_bytes': size_bytes,
                            'size_mb': round(size_bytes / (1024 * 1024), 2),
                            'is_binary': is_binary,
                            'location': 'history'
                        })
            except ValueError:
                continue
                
        return large_objects
    
    def get_large_files_in_working_tree(self) -> List[Dict]:
        """Find large files in current working tree"""
        print("🔍 Scanning working tree for large files...")
        
        large_files = []
        
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and not self.is_git_internal_file(file_path):
                try:
                    size_bytes = file_path.stat().st_size
                    
                    if size_bytes > self.size_threshold_bytes:
                        is_binary = self.is_likely_binary(str(file_path))
                        
                        # Check if file is tracked by git
                        is_tracked = self.is_file_tracked(file_path)
                        
                        large_files.append({
                            'path': str(file_path.relative_to(self.repo_path)),
                            'size_bytes': size_bytes,
                            'size_mb': round(size_bytes / (1024 * 1024), 2),
                            'is_binary': is_binary,
                            'is_tracked': is_tracked,
                            'location': 'working_tree'
                        })
                except (OSError, ValueError):
                    continue
                    
        return large_files
    
    def is_git_internal_file(self, file_path: Path) -> bool:
        """Check if file is git internal (.git directory, etc.)"""
        try:
            relative_path = file_path.relative_to(self.repo_path)
            return str(relative_path).startswith('.git/')
        except ValueError:
            return False
    
    def is_file_tracked(self, file_path: Path) -> bool:
        """Check if file is tracked by git"""
        try:
            relative_path = file_path.relative_to(self.repo_path)
            result = subprocess.run(
                ['git', 'ls-files', '--error-unmatch', str(relative_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except ValueError:
            return False
    
    def is_likely_binary(self, file_path: str) -> bool:
        """Determine if file is likely binary based on extension"""
        path = Path(file_path)
        return path.suffix.lower() in self.binary_extensions
    
    def suggest_migration_strategy(self, file_info: Dict) -> Dict:
        """Suggest migration strategy for large file"""
        file_path = file_info['path']
        size_mb = file_info['size_mb']
        is_binary = file_info['is_binary']
        
        # Determine file category
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        
        if extension in ['.safetensors', '.bin', '.pt', '.pth', '.ckpt', '.h5']:
            category = 'model_weights'
            storage_location = 's3://gameforge-models/'
            action = 'move_to_s3_create_manifest'
        elif extension in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']:
            category = 'image_dataset'
            storage_location = 's3://gameforge-datasets/images/'
            action = 'move_to_s3_update_dataset_manifest'
        elif extension in ['.mp4', '.avi', '.mov', '.wav', '.mp3', '.flac']:
            category = 'media_assets'
            storage_location = 's3://gameforge-assets/media/'
            action = 'move_to_s3_update_asset_registry'
        elif extension in ['.zip', '.tar', '.gz', '.bz2']:
            category = 'archive'
            storage_location = 's3://gameforge-datasets/archives/'
            action = 'extract_and_migrate_contents'
        else:
            category = 'unknown_binary' if is_binary else 'large_text'
            storage_location = 's3://gameforge-artifacts/'
            action = 'review_and_migrate'
        
        return {
            'category': category,
            'storage_location': storage_location,
            'action': action,
            'priority': 'high' if size_mb > 100 else 'medium' if size_mb > 50 else 'low',
            'steps': self.get_migration_steps(file_info, category, storage_location)
        }
    
    def get_migration_steps(self, file_info: Dict, category: str, storage_location: str) -> List[str]:
        """Get specific migration steps for file"""
        file_path = file_info['path']
        
        if category == 'model_weights':
            return [
                f"1. Upload {file_path} to {storage_location}",
                f"2. Create manifest in models/manifests/{Path(file_path).stem}.yaml",
                f"3. Add SHA256 hash and metadata to manifest",
                f"4. Remove {file_path} from git: git rm {file_path}",
                f"5. Update code to load from S3 using manifest",
                f"6. Commit removal: git commit -m 'Move {file_path} to external storage'"
            ]
        elif category == 'image_dataset':
            return [
                f"1. Upload {file_path} to {storage_location}",
                f"2. Update datasets/dataset-manifest.yaml with new shard",
                f"3. Remove {file_path} from git: git rm {file_path}",
                f"4. Update preprocessing scripts to use S3 location",
                f"5. Commit changes"
            ]
        else:
            return [
                f"1. Review {file_path} to determine if needed",
                f"2. If needed, upload to {storage_location}",
                f"3. Update references in code/documentation",
                f"4. Remove from git: git rm {file_path}",
                f"5. Commit removal"
            ]
    
    def generate_report(self, history_objects: List[Dict], working_tree_files: List[Dict]) -> Dict:
        """Generate comprehensive report"""
        all_files = history_objects + working_tree_files
        
        # Statistics
        total_files = len(all_files)
        total_size_mb = sum(f['size_mb'] for f in all_files)
        binary_files = [f for f in all_files if f['is_binary']]
        
        # Categorize files
        categories = {}
        for file_info in all_files:
            migration = self.suggest_migration_strategy(file_info)
            category = migration['category']
            if category not in categories:
                categories[category] = []
            categories[category].append({**file_info, 'migration': migration})
        
        return {
            'timestamp': datetime.now().isoformat(),
            'repository_path': str(self.repo_path),
            'threshold_mb': self.size_threshold_mb,
            'statistics': {
                'total_large_files': total_files,
                'total_size_mb': round(total_size_mb, 2),
                'binary_files_count': len(binary_files),
                'history_objects': len(history_objects),
                'working_tree_files': len(working_tree_files)
            },
            'categories': categories,
            'recommendations': self.generate_recommendations(categories)
        }
    
    def generate_recommendations(self, categories: Dict) -> List[Dict]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        
        for category, files in categories.items():
            for file_info in files:
                migration = file_info['migration']
                recommendations.append({
                    'file': file_info['path'],
                    'size_mb': file_info['size_mb'],
                    'category': category,
                    'priority': migration['priority'],
                    'action': migration['action'],
                    'storage_location': migration['storage_location'],
                    'steps': migration['steps']
                })
        
        # Sort by priority and size
        recommendations.sort(key=lambda x: (priority_order[x['priority']], -x['size_mb']))
        
        return recommendations


def main():
    """Main execution function"""
    print("🔍 GameForge Large File Detection - Copilot Security Check")
    print("=" * 60)
    
    detector = LargeFileDetector()
    
    if not detector.is_git_repo():
        print("❌ Error: Not a git repository")
        sys.exit(1)
    
    print(f"📁 Repository: {detector.repo_path}")
    print(f"📏 Size threshold: {detector.size_threshold_mb}MB")
    print()
    
    # Scan git history
    history_objects = detector.get_large_objects_from_history()
    
    # Scan working tree
    working_tree_files = detector.get_large_files_in_working_tree()
    
    # Generate report
    report = detector.generate_report(history_objects, working_tree_files)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 LARGE FILE ANALYSIS RESULTS")
    print("=" * 60)
    
    stats = report['statistics']
    print(f"Total large files found: {stats['total_large_files']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Binary files: {stats['binary_files_count']}")
    print(f"In git history: {stats['history_objects']}")
    print(f"In working tree: {stats['working_tree_files']}")
    
    if stats['total_large_files'] == 0:
        print("\n✅ No large files found! Repository is compliant.")
        return
    
    print(f"\n❌ POLICY VIOLATION: {stats['total_large_files']} large files detected")
    
    # Show categories
    print(f"\n📂 FILES BY CATEGORY:")
    for category, files in report['categories'].items():
        print(f"  {category}: {len(files)} files")
    
    # Show top recommendations
    print(f"\n🔧 TOP MIGRATION RECOMMENDATIONS:")
    for i, rec in enumerate(report['recommendations'][:10], 1):
        print(f"\n{i}. {rec['file']} ({rec['size_mb']}MB)")
        print(f"   Priority: {rec['priority'].upper()}")
        print(f"   Action: {rec['action']}")
        print(f"   Storage: {rec['storage_location']}")
    
    # Save detailed report
    report_file = detector.repo_path / "large_files_analysis.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved: {report_file}")
    
    # Exit with error code if violations found
    sys.exit(1)


if __name__ == "__main__":
    main()
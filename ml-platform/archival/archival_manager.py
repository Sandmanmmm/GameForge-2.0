#!/usr/bin/env python3
"""
GameForge ML Archival and Cleanup System

Automated archival, cleanup, and lifecycle management for ML artifacts.
Integrates with CI/CD for large file management and compliance.
"""

import os
import json
import shutil
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import logging
import yaml
import subprocess
import boto3
from botocore.exceptions import ClientError
import pandas as pd
import tempfile


@dataclass
class ArchivalPolicy:
    """Archival policy configuration"""
    name: str
    description: str
    retention_days: int
    storage_class: str  # standard, ia, glacier, deep_archive
    auto_delete_days: Optional[int]
    compliance_required: bool
    size_threshold_mb: Optional[int]
    file_patterns: List[str]


@dataclass
class CleanupResult:
    """Results from cleanup operation"""
    files_archived: int
    files_deleted: int
    bytes_freed: int
    bytes_archived: int
    errors: List[str]
    warnings: List[str]


@dataclass
class LargeFileInfo:
    """Information about large files"""
    path: str
    size_bytes: int
    last_modified: datetime
    git_tracked: bool
    commit_hash: Optional[str]
    usage_count: int
    recommended_action: str


class MLArchivalManager:
    """
    ML Archival and Cleanup Manager
    
    Handles:
    - Automated archival of old models and datasets
    - Large file detection and migration
    - Git repository cleanup
    - Compliance and retention management
    - Storage optimization
    """
    
    def __init__(self, config_path: str = None):
        """Initialize archival manager"""
        
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "archival-config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize storage and database
        self._init_storage()
        self._init_database()
        
        # Load archival policies
        self._load_archival_policies()
        
        self.logger.info("✅ ML Archival Manager initialized")
    
    
    def _setup_logging(self):
        """Setup archival logging"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "archival.log"),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    
    def _init_storage(self):
        """Initialize S3 storage for archives"""
        self.s3_client = boto3.client('s3')
        self.archive_bucket = self.config['storage']['archive_bucket']
        self.archive_prefix = self.config['storage']['archive_prefix']
    
    
    def _init_database(self):
        """Initialize archival database"""
        db_path = Path(__file__).parent / "archival.db"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_archival_tables()
    
    
    def _load_archival_policies(self):
        """Load archival policies from configuration"""
        self.policies = {}
        
        for policy_config in self.config.get('policies', []):
            policy = ArchivalPolicy(
                name=policy_config['name'],
                description=policy_config['description'],
                retention_days=policy_config['retention_days'],
                storage_class=policy_config.get('storage_class', 'standard'),
                auto_delete_days=policy_config.get('auto_delete_days'),
                compliance_required=policy_config.get('compliance_required', False),
                size_threshold_mb=policy_config.get('size_threshold_mb'),
                file_patterns=policy_config.get('file_patterns', [])
            )
            self.policies[policy.name] = policy
    
    
    def _create_archival_tables(self):
        """Create database tables for archival tracking"""
        
        # Archived items table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS archived_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                archive_location TEXT NOT NULL,
                archive_type TEXT NOT NULL,
                file_size BIGINT NOT NULL,
                archived_at TIMESTAMP NOT NULL,
                policy_name TEXT NOT NULL,
                retention_until TIMESTAMP,
                checksum TEXT NOT NULL,
                metadata TEXT,
                restored BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Cleanup history table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                target_path TEXT NOT NULL,
                files_processed INTEGER NOT NULL,
                bytes_processed BIGINT NOT NULL,
                executed_at TIMESTAMP NOT NULL,
                policy_applied TEXT,
                status TEXT NOT NULL,
                error_message TEXT
            )
        ''')
        
        # Large files tracking table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS large_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_size BIGINT NOT NULL,
                discovered_at TIMESTAMP NOT NULL,
                last_checked TIMESTAMP NOT NULL,
                git_tracked BOOLEAN NOT NULL,
                action_taken TEXT,
                action_date TIMESTAMP,
                notes TEXT
            )
        ''')
        
        self.conn.commit()
    
    
    def scan_large_files(self, 
                        directory: str,
                        size_threshold_mb: int = 100,
                        exclude_patterns: List[str] = None) -> List[LargeFileInfo]:
        """
        Scan directory for large files that should be archived
        
        Args:
            directory: Directory to scan
            size_threshold_mb: Size threshold in MB
            exclude_patterns: Patterns to exclude from scan
            
        Returns:
            List of LargeFileInfo objects
        """
        
        large_files = []
        size_threshold_bytes = size_threshold_mb * 1024 * 1024
        
        exclude_patterns = exclude_patterns or [
            '*.git/*', '*.venv/*', '*/__pycache__/*', '*/node_modules/*'
        ]
        
        self.logger.info(f"Scanning for files > {size_threshold_mb}MB in {directory}")
        
        try:
            # Check if directory is a git repository
            is_git_repo = self._is_git_repository(directory)
            git_files = set()
            
            if is_git_repo:
                git_files = self._get_git_tracked_files(directory)
            
            # Scan directory
            for root, dirs, files in os.walk(directory):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if not any(
                    self._matches_pattern(os.path.join(root, d), pattern)
                    for pattern in exclude_patterns
                )]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip excluded files
                    if any(self._matches_pattern(file_path, pattern) for pattern in exclude_patterns):
                        continue
                    
                    try:
                        stat = os.stat(file_path)
                        
                        if stat.st_size >= size_threshold_bytes:
                            relative_path = os.path.relpath(file_path, directory)
                            
                            # Check if file is git tracked
                            git_tracked = relative_path in git_files
                            
                            # Get commit info if git tracked
                            commit_hash = None
                            if git_tracked and is_git_repo:
                                commit_hash = self._get_file_commit_hash(directory, relative_path)
                            
                            # Determine recommended action
                            recommended_action = self._recommend_large_file_action(
                                file_path, stat.st_size, git_tracked
                            )
                            
                            large_file = LargeFileInfo(
                                path=file_path,
                                size_bytes=stat.st_size,
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                git_tracked=git_tracked,
                                commit_hash=commit_hash,
                                usage_count=0,  # Could be enhanced with actual usage tracking
                                recommended_action=recommended_action
                            )
                            
                            large_files.append(large_file)
                            
                            # Store in database
                            self._store_large_file_info(large_file)
                    
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Could not stat file {file_path}: {e}")
            
            self.logger.info(f"Found {len(large_files)} large files")
            return large_files
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {e}")
            return large_files
    
    
    def _is_git_repository(self, directory: str) -> bool:
        """Check if directory is a git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    
    def _get_git_tracked_files(self, directory: str) -> Set[str]:
        """Get set of git tracked files"""
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            return set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
        except subprocess.CalledProcessError:
            return set()
    
    
    def _get_file_commit_hash(self, directory: str, file_path: str) -> Optional[str]:
        """Get latest commit hash for a file"""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H', '--', file_path],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() if result.stdout.strip() else None
        except subprocess.CalledProcessError:
            return None
    
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches exclusion pattern"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
    
    
    def _recommend_large_file_action(self, file_path: str, size_bytes: int, git_tracked: bool) -> str:
        """Recommend action for large file"""
        
        size_mb = size_bytes / (1024 * 1024)
        
        # Check file extension
        ext = Path(file_path).suffix.lower()
        
        # Model files
        if ext in ['.pth', '.pt', '.ckpt', '.pkl', '.joblib', '.h5', '.pb', '.onnx']:
            if git_tracked:
                return "migrate_to_lfs_and_s3"
            else:
                return "move_to_s3"
        
        # Dataset files
        elif ext in ['.csv', '.parquet', '.jsonl', '.txt', '.json']:
            if size_mb > 500:
                return "move_to_s3"
            elif git_tracked:
                return "migrate_to_lfs"
            else:
                return "keep_local"
        
        # Binary files
        elif ext in ['.zip', '.tar', '.gz', '.bz2', '.7z']:
            return "move_to_s3"
        
        # Media files
        elif ext in ['.jpg', '.png', '.mp4', '.wav', '.mp3']:
            if git_tracked:
                return "migrate_to_lfs"
            else:
                return "move_to_s3"
        
        # Large text files
        elif size_mb > 1000:
            return "compress_and_archive"
        
        else:
            return "review_manually"
    
    
    def _store_large_file_info(self, large_file: LargeFileInfo):
        """Store large file information in database"""
        
        now = datetime.utcnow()
        
        self.conn.execute('''
            INSERT OR REPLACE INTO large_files
            (file_path, file_size, discovered_at, last_checked, git_tracked, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            large_file.path,
            large_file.size_bytes,
            now,
            now,
            large_file.git_tracked,
            f"Recommended: {large_file.recommended_action}"
        ))
        
        self.conn.commit()
    
    
    def migrate_large_file_to_s3(self, 
                                file_path: str,
                                remove_local: bool = True,
                                create_pointer: bool = True) -> Tuple[bool, str]:
        """
        Migrate large file to S3 storage
        
        Args:
            file_path: Path to file to migrate
            remove_local: Whether to remove local file after upload
            create_pointer: Whether to create a pointer file
            
        Returns:
            Tuple of (success, s3_location or error_message)
        """
        
        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)
            
            # Generate S3 key
            file_name = Path(file_path).name
            s3_key = f"{self.archive_prefix}/large-files/{file_hash[:2]}/{file_hash[2:4]}/{file_hash}_{file_name}"
            
            # Upload to S3
            self.logger.info(f"Uploading {file_path} to s3://{self.archive_bucket}/{s3_key}")
            
            self.s3_client.upload_file(
                file_path,
                self.archive_bucket,
                s3_key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',
                    'Metadata': {
                        'original_path': file_path,
                        'uploaded_at': datetime.utcnow().isoformat(),
                        'file_hash': file_hash
                    }
                }
            )
            
            s3_location = f"s3://{self.archive_bucket}/{s3_key}"
            
            # Create pointer file if requested
            if create_pointer:
                self._create_pointer_file(file_path, s3_location, file_hash)
            
            # Remove local file if requested
            if remove_local:
                os.remove(file_path)
                self.logger.info(f"Removed local file: {file_path}")
            
            # Record archival
            self._record_archival(file_path, s3_location, os.path.getsize(file_path) if not remove_local else 0)
            
            return True, s3_location
            
        except Exception as e:
            self.logger.error(f"Failed to migrate {file_path}: {e}")
            return False, str(e)
    
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    
    def _create_pointer_file(self, original_path: str, s3_location: str, file_hash: str):
        """Create pointer file referencing S3 location"""
        
        pointer_content = {
            "version": "1.0",
            "type": "s3_pointer",
            "s3_location": s3_location,
            "file_hash": file_hash,
            "created_at": datetime.utcnow().isoformat(),
            "instructions": {
                "download": f"aws s3 cp {s3_location} .",
                "restore": f"python -m ml_platform.archival restore {file_hash}"
            }
        }
        
        pointer_path = f"{original_path}.s3_pointer.json"
        
        with open(pointer_path, 'w') as f:
            json.dump(pointer_content, f, indent=2)
        
        self.logger.info(f"Created pointer file: {pointer_path}")
    
    
    def _record_archival(self, original_path: str, archive_location: str, file_size: int):
        """Record archival operation in database"""
        
        self.conn.execute('''
            INSERT INTO archived_items
            (original_path, archive_location, archive_type, file_size, archived_at, 
             policy_name, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            original_path,
            archive_location,
            's3_migration',
            file_size,
            datetime.utcnow(),
            'large_file_migration',
            self._calculate_file_hash(original_path) if os.path.exists(original_path) else 'unknown'
        ))
        
        self.conn.commit()
    
    
    def restore_file_from_s3(self, file_hash: str, target_path: str = None) -> Tuple[bool, str]:
        """
        Restore file from S3 using hash
        
        Args:
            file_hash: SHA256 hash of file
            target_path: Where to restore file (optional)
            
        Returns:
            Tuple of (success, local_path or error_message)
        """
        
        try:
            # Find archived item
            cursor = self.conn.execute('''
                SELECT original_path, archive_location, file_size
                FROM archived_items
                WHERE checksum = ? AND archive_type = 's3_migration'
            ''', (file_hash,))
            
            row = cursor.fetchone()
            if not row:
                return False, f"File with hash {file_hash} not found in archive"
            
            original_path, archive_location, file_size = row
            
            # Determine target path
            if target_path is None:
                target_path = original_path
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Parse S3 location
            if archive_location.startswith('s3://'):
                bucket, key = archive_location[5:].split('/', 1)
            else:
                return False, f"Invalid archive location: {archive_location}"
            
            # Download from S3
            self.logger.info(f"Restoring {archive_location} to {target_path}")
            
            self.s3_client.download_file(bucket, key, target_path)
            
            # Verify hash
            restored_hash = self._calculate_file_hash(target_path)
            if restored_hash != file_hash:
                os.remove(target_path)
                return False, f"Hash verification failed: expected {file_hash}, got {restored_hash}"
            
            # Update database
            self.conn.execute('''
                UPDATE archived_items
                SET restored = TRUE
                WHERE checksum = ? AND archive_type = 's3_migration'
            ''', (file_hash,))
            
            self.conn.commit()
            
            self.logger.info(f"✅ File restored: {target_path}")
            return True, target_path
            
        except Exception as e:
            self.logger.error(f"Failed to restore file: {e}")
            return False, str(e)
    
    
    def cleanup_old_artifacts(self, 
                             target_directory: str,
                             dry_run: bool = True) -> CleanupResult:
        """
        Clean up old ML artifacts based on policies
        
        Args:
            target_directory: Directory to clean up
            dry_run: Whether to perform actual cleanup or just report
            
        Returns:
            CleanupResult with cleanup statistics
        """
        
        result = CleanupResult(
            files_archived=0,
            files_deleted=0,
            bytes_freed=0,
            bytes_archived=0,
            errors=[],
            warnings=[]
        )
        
        try:
            self.logger.info(f"Starting cleanup of {target_directory} (dry_run={dry_run})")
            
            # Apply each policy
            for policy_name, policy in self.policies.items():
                self.logger.info(f"Applying policy: {policy_name}")
                
                policy_result = self._apply_cleanup_policy(
                    target_directory, policy, dry_run
                )
                
                # Aggregate results
                result.files_archived += policy_result.files_archived
                result.files_deleted += policy_result.files_deleted
                result.bytes_freed += policy_result.bytes_freed
                result.bytes_archived += policy_result.bytes_archived
                result.errors.extend(policy_result.errors)
                result.warnings.extend(policy_result.warnings)
            
            # Record cleanup operation
            if not dry_run:
                self._record_cleanup_operation(target_directory, result)
            
            self.logger.info(f"Cleanup completed: {result.files_archived} archived, {result.files_deleted} deleted")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            result.errors.append(str(e))
            return result
    
    
    def _apply_cleanup_policy(self, 
                             directory: str, 
                             policy: ArchivalPolicy, 
                             dry_run: bool) -> CleanupResult:
        """Apply specific cleanup policy"""
        
        result = CleanupResult(
            files_archived=0,
            files_deleted=0,
            bytes_freed=0,
            bytes_archived=0,
            errors=[],
            warnings=[]
        )
        
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
        
        try:
            for pattern in policy.file_patterns:
                for file_path in Path(directory).glob(pattern):
                    if not file_path.is_file():
                        continue
                    
                    # Check file age
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime > cutoff_date:
                        continue
                    
                    # Check size threshold if specified
                    file_size = file_path.stat().st_size
                    if policy.size_threshold_mb:
                        size_threshold_bytes = policy.size_threshold_mb * 1024 * 1024
                        if file_size < size_threshold_bytes:
                            continue
                    
                    # Apply policy action
                    if policy.auto_delete_days:
                        delete_cutoff = datetime.utcnow() - timedelta(days=policy.auto_delete_days)
                        
                        if file_mtime < delete_cutoff:
                            # Delete file
                            if not dry_run:
                                file_path.unlink()
                                self.logger.info(f"Deleted: {file_path}")
                            
                            result.files_deleted += 1
                            result.bytes_freed += file_size
                        else:
                            # Archive file
                            if not dry_run:
                                success, location = self._archive_file(str(file_path), policy)
                                if success:
                                    result.files_archived += 1
                                    result.bytes_archived += file_size
                                else:
                                    result.errors.append(f"Failed to archive {file_path}: {location}")
                            else:
                                result.files_archived += 1
                                result.bytes_archived += file_size
                    else:
                        # Just archive
                        if not dry_run:
                            success, location = self._archive_file(str(file_path), policy)
                            if success:
                                result.files_archived += 1
                                result.bytes_archived += file_size
                            else:
                                result.errors.append(f"Failed to archive {file_path}: {location}")
                        else:
                            result.files_archived += 1
                            result.bytes_archived += file_size
        
        except Exception as e:
            result.errors.append(f"Policy {policy.name} failed: {e}")
        
        return result
    
    
    def _archive_file(self, file_path: str, policy: ArchivalPolicy) -> Tuple[bool, str]:
        """Archive file according to policy"""
        
        try:
            file_hash = self._calculate_file_hash(file_path)
            file_name = Path(file_path).name
            
            # Generate archive key
            date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
            s3_key = f"{self.archive_prefix}/{policy.name}/{date_prefix}/{file_hash}_{file_name}"
            
            # Upload to S3 with appropriate storage class
            self.s3_client.upload_file(
                file_path,
                self.archive_bucket,
                s3_key,
                ExtraArgs={
                    'StorageClass': policy.storage_class.upper(),
                    'Metadata': {
                        'policy': policy.name,
                        'archived_at': datetime.utcnow().isoformat(),
                        'original_path': file_path,
                        'file_hash': file_hash
                    }
                }
            )
            
            s3_location = f"s3://{self.archive_bucket}/{s3_key}"
            
            # Record archival
            retention_until = None
            if policy.auto_delete_days:
                retention_until = datetime.utcnow() + timedelta(days=policy.auto_delete_days)
            
            self.conn.execute('''
                INSERT INTO archived_items
                (original_path, archive_location, archive_type, file_size, archived_at,
                 policy_name, retention_until, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_path,
                s3_location,
                'policy_archive',
                os.path.getsize(file_path),
                datetime.utcnow(),
                policy.name,
                retention_until,
                file_hash
            ))
            
            self.conn.commit()
            
            # Remove local file
            os.remove(file_path)
            
            return True, s3_location
            
        except Exception as e:
            return False, str(e)
    
    
    def _record_cleanup_operation(self, target_directory: str, result: CleanupResult):
        """Record cleanup operation in database"""
        
        self.conn.execute('''
            INSERT INTO cleanup_history
            (operation_type, target_path, files_processed, bytes_processed,
             executed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'policy_cleanup',
            target_directory,
            result.files_archived + result.files_deleted,
            result.bytes_freed + result.bytes_archived,
            datetime.utcnow(),
            'success' if not result.errors else 'partial_success'
        ))
        
        self.conn.commit()
    
    
    def generate_git_cleanup_script(self, repository_path: str) -> str:
        """Generate script to clean up large files from git history"""
        
        script_lines = [
            "#!/bin/bash",
            "# GameForge Git Cleanup Script",
            "# WARNING: This will rewrite git history. Make sure you have backups!",
            "",
            "set -e",
            "",
            "echo '🚀 Starting Git cleanup...'",
            "",
            "# Create backup branch",
            "git branch backup-before-cleanup || true",
            "",
            "# Get list of large files from git history",
            "echo '📋 Finding large files in git history...'",
        ]
        
        # Get large files from git history
        try:
            large_files = self._get_large_files_from_git_history(repository_path)
            
            if large_files:
                script_lines.extend([
                    "",
                    "# Large files found in history:",
                ])
                
                for file_path, size_mb in large_files[:20]:  # Limit to top 20
                    script_lines.append(f"# {file_path} ({size_mb:.1f} MB)")
                
                script_lines.extend([
                    "",
                    "# Remove large files from git history",
                    "echo '🗑️  Removing large files from git history...'",
                ])
                
                for file_path, _ in large_files[:10]:  # Only remove top 10 automatically
                    escaped_path = file_path.replace("'", "'\"'\"'")
                    script_lines.append(f"git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch \"{escaped_path}\"' --prune-empty --tag-name-filter cat -- --all || true")
                
                script_lines.extend([
                    "",
                    "# Clean up refs",
                    "echo '🧹 Cleaning up references...'",
                    "rm -rf .git/refs/original/",
                    "git reflog expire --expire=now --all",
                    "git gc --prune=now --aggressive",
                    "",
                    "echo '✅ Git cleanup completed!'",
                    "echo '📊 Repository size before/after:'",
                    "du -sh .git/",
                    "",
                    "echo '⚠️  IMPORTANT: Force push required to update remote repository:'",
                    "echo '   git push origin --force --all'",
                    "echo '   git push origin --force --tags'",
                ])
            else:
                script_lines.extend([
                    "",
                    "echo '✅ No large files found in git history!'",
                ])
        
        except Exception as e:
            script_lines.extend([
                "",
                f"echo '❌ Error analyzing git history: {e}'",
                "exit 1",
            ])
        
        return '\n'.join(script_lines)
    
    
    def _get_large_files_from_git_history(self, repo_path: str, threshold_mb: int = 10) -> List[Tuple[str, float]]:
        """Get large files from git history"""
        
        try:
            # Use git rev-list to find all objects
            result = subprocess.run([
                'git', 'rev-list', '--objects', '--all'
            ], cwd=repo_path, capture_output=True, text=True, check=True)
            
            object_list = result.stdout.strip().split('\n')
            large_files = []
            
            for line in object_list:
                if not line.strip():
                    continue
                
                parts = line.split(' ', 1)
                if len(parts) != 2:
                    continue
                
                object_hash, file_path = parts
                
                # Get object size
                try:
                    size_result = subprocess.run([
                        'git', 'cat-file', '-s', object_hash
                    ], cwd=repo_path, capture_output=True, text=True, check=True)
                    
                    size_bytes = int(size_result.stdout.strip())
                    size_mb = size_bytes / (1024 * 1024)
                    
                    if size_mb >= threshold_mb:
                        large_files.append((file_path, size_mb))
                
                except (subprocess.CalledProcessError, ValueError):
                    continue
            
            # Sort by size (largest first) and remove duplicates
            large_files = sorted(set(large_files), key=lambda x: x[1], reverse=True)
            
            return large_files
        
        except subprocess.CalledProcessError:
            return []
    
    
    def get_archival_statistics(self) -> Dict[str, any]:
        """Get archival and cleanup statistics"""
        
        stats = {}
        
        # Archived items stats
        cursor = self.conn.execute('''
            SELECT 
                COUNT(*) as total_archived,
                SUM(file_size) as total_bytes_archived,
                COUNT(DISTINCT policy_name) as policies_used
            FROM archived_items
        ''')
        
        row = cursor.fetchone()
        stats['archived_items'] = {
            'total_count': row[0],
            'total_bytes': row[1] or 0,
            'total_gb': (row[1] or 0) / (1024**3),
            'policies_used': row[2]
        }
        
        # Cleanup history stats
        cursor = self.conn.execute('''
            SELECT 
                COUNT(*) as total_operations,
                SUM(files_processed) as total_files,
                SUM(bytes_processed) as total_bytes
            FROM cleanup_history
            WHERE executed_at > datetime('now', '-30 days')
        ''')
        
        row = cursor.fetchone()
        stats['recent_cleanup'] = {
            'operations_last_30_days': row[0],
            'files_processed': row[1] or 0,
            'bytes_processed': row[2] or 0,
            'gb_processed': (row[2] or 0) / (1024**3)
        }
        
        # Large files stats
        cursor = self.conn.execute('''
            SELECT 
                COUNT(*) as total_large_files,
                SUM(file_size) as total_size,
                COUNT(CASE WHEN action_taken IS NOT NULL THEN 1 END) as actions_taken
            FROM large_files
        ''')
        
        row = cursor.fetchone()
        stats['large_files'] = {
            'total_discovered': row[0],
            'total_size_bytes': row[1] or 0,
            'total_size_gb': (row[1] or 0) / (1024**3),
            'actions_taken': row[2]
        }
        
        return stats


def main():
    """CLI interface for archival manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge ML Archival Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan large files
    scan_parser = subparsers.add_parser('scan', help='Scan for large files')
    scan_parser.add_argument('--directory', required=True, help='Directory to scan')
    scan_parser.add_argument('--threshold', type=int, default=100, help='Size threshold in MB')
    
    # Migrate file to S3
    migrate_parser = subparsers.add_parser('migrate', help='Migrate file to S3')
    migrate_parser.add_argument('--file', required=True, help='File to migrate')
    migrate_parser.add_argument('--keep-local', action='store_true', help='Keep local file')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old artifacts')
    cleanup_parser.add_argument('--directory', required=True, help='Directory to clean up')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    
    # Restore file
    restore_parser = subparsers.add_parser('restore', help='Restore file from S3')
    restore_parser.add_argument('--hash', required=True, help='File hash')
    restore_parser.add_argument('--target', help='Target path')
    
    # Git cleanup script
    git_parser = subparsers.add_parser('git-cleanup', help='Generate git cleanup script')
    git_parser.add_argument('--repo', required=True, help='Git repository path')
    git_parser.add_argument('--output', help='Output script file')
    
    # Statistics
    stats_parser = subparsers.add_parser('stats', help='Show archival statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize archival manager
    manager = MLArchivalManager()
    
    try:
        if args.command == 'scan':
            large_files = manager.scan_large_files(
                directory=args.directory,
                size_threshold_mb=args.threshold
            )
            
            print(f"\n🔍 Large Files Report:")
            print(f"   Directory: {args.directory}")
            print(f"   Threshold: {args.threshold} MB")
            print(f"   Found: {len(large_files)} files")
            
            total_size = sum(f.size_bytes for f in large_files)
            print(f"   Total size: {total_size / (1024**3):.2f} GB")
            
            for file_info in large_files[:10]:  # Show top 10
                size_mb = file_info.size_bytes / (1024**2)
                git_status = "📝 tracked" if file_info.git_tracked else "📁 untracked"
                print(f"   {file_info.path}: {size_mb:.1f} MB {git_status} → {file_info.recommended_action}")
        
        elif args.command == 'migrate':
            success, result = manager.migrate_large_file_to_s3(
                file_path=args.file,
                remove_local=not args.keep_local
            )
            
            if success:
                print(f"✅ File migrated to: {result}")
            else:
                print(f"❌ Migration failed: {result}")
        
        elif args.command == 'cleanup':
            result = manager.cleanup_old_artifacts(
                target_directory=args.directory,
                dry_run=args.dry_run
            )
            
            print(f"\n🧹 Cleanup Results:")
            print(f"   Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
            print(f"   Files archived: {result.files_archived}")
            print(f"   Files deleted: {result.files_deleted}")
            print(f"   Bytes freed: {result.bytes_freed / (1024**3):.2f} GB")
            print(f"   Bytes archived: {result.bytes_archived / (1024**3):.2f} GB")
            
            if result.errors:
                print(f"   Errors: {len(result.errors)}")
                for error in result.errors[:5]:
                    print(f"     {error}")
        
        elif args.command == 'restore':
            success, result = manager.restore_file_from_s3(
                file_hash=args.hash,
                target_path=args.target
            )
            
            if success:
                print(f"✅ File restored to: {result}")
            else:
                print(f"❌ Restore failed: {result}")
        
        elif args.command == 'git-cleanup':
            script = manager.generate_git_cleanup_script(args.repo)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(script)
                os.chmod(args.output, 0o755)
                print(f"✅ Git cleanup script written to: {args.output}")
            else:
                print(script)
        
        elif args.command == 'stats':
            stats = manager.get_archival_statistics()
            
            print(f"\n📊 Archival Statistics:")
            print(f"   Archived items: {stats['archived_items']['total_count']}")
            print(f"   Total archived: {stats['archived_items']['total_gb']:.2f} GB")
            print(f"   Recent cleanup operations: {stats['recent_cleanup']['operations_last_30_days']}")
            print(f"   Large files discovered: {stats['large_files']['total_discovered']}")
            print(f"   Total large file size: {stats['large_files']['total_size_gb']:.2f} GB")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
GameForge AI Model Management System
Handles model lifecycle, versioning, and deployment
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.manifest_file = os.path.join(models_dir, "models_manifest.json")
        self.ensure_models_dir()
    
    def ensure_models_dir(self):
        """Ensure models directory exists"""
        os.makedirs(self.models_dir, exist_ok=True)
    
    def get_model_manifest(self) -> Dict:
        """Get current model manifest"""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {"models": {}, "last_updated": None}
    
    def update_manifest(self, manifest: Dict):
        """Update model manifest"""
        manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def calculate_model_hash(self, model_path: str) -> str:
        """Calculate hash of model files for verification"""
        hash_md5 = hashlib.md5()
        
        if os.path.isfile(model_path):
            with open(model_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        elif os.path.isdir(model_path):
            for root, dirs, files in os.walk(model_path):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def register_model(self, model_name: str, model_path: str, model_type: str, version: str = "1.0.0"):
        """Register a model in the manifest"""
        manifest = self.get_model_manifest()
        
        model_info = {
            "path": model_path,
            "type": model_type,
            "version": version,
            "size_bytes": self.get_directory_size(model_path),
            "hash": self.calculate_model_hash(model_path),
            "registered_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0
        }
        
        manifest["models"][model_name] = model_info
        self.update_manifest(manifest)
        
        logger.info(f"✅ Model {model_name} registered successfully")
    
    def get_directory_size(self, path: str) -> int:
        """Get total size of directory"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size
    
    def list_models(self) -> Dict:
        """List all registered models"""
        manifest = self.get_model_manifest()
        return manifest.get("models", {})
    
    def verify_model_integrity(self, model_name: str) -> bool:
        """Verify model integrity using hash"""
        manifest = self.get_model_manifest()
        
        if model_name not in manifest["models"]:
            logger.error(f"Model {model_name} not found in manifest")
            return False
        
        model_info = manifest["models"][model_name]
        model_path = os.path.join(self.models_dir, model_info["path"])
        
        if not os.path.exists(model_path):
            logger.error(f"Model path {model_path} does not exist")
            return False
        
        current_hash = self.calculate_model_hash(model_path)
        expected_hash = model_info["hash"]
        
        if current_hash != expected_hash:
            logger.error(f"Model {model_name} integrity check failed")
            return False
        
        logger.info(f"✅ Model {model_name} integrity verified")
        return True
    
    def cleanup_unused_models(self, days_unused: int = 30):
        """Clean up models not used for specified days"""
        manifest = self.get_model_manifest()
        current_time = datetime.now()
        
        for model_name, model_info in list(manifest["models"].items()):
            last_used = model_info.get("last_used")
            
            if last_used:
                last_used_date = datetime.fromisoformat(last_used)
                days_since_used = (current_time - last_used_date).days
                
                if days_since_used > days_unused:
                    model_path = os.path.join(self.models_dir, model_info["path"])
                    if os.path.exists(model_path):
                        shutil.rmtree(model_path)
                        logger.info(f"🗑️  Removed unused model: {model_name}")
                    
                    del manifest["models"][model_name]
        
        self.update_manifest(manifest)
    
    def generate_model_report(self) -> str:
        """Generate model usage report"""
        manifest = self.get_model_manifest()
        models = manifest.get("models", {})
        
        report = []
        report.append("=" * 60)
        report.append("GAMEFORGE AI - MODEL MANAGEMENT REPORT")
        report.append("=" * 60)
        report.append("")
        
        if not models:
            report.append("No models registered")
            return "\n".join(report)
        
        total_size = sum(model["size_bytes"] for model in models.values())
        
        report.append(f"Total Models: {len(models)}")
        report.append(f"Total Size: {total_size / (1024**3):.2f} GB")
        report.append("")
        
        report.append("MODEL DETAILS:")
        report.append("-" * 40)
        
        for name, info in models.items():
            size_gb = info["size_bytes"] / (1024**3)
            last_used = info.get("last_used", "Never")
            report.append(f"• {name}")
            report.append(f"  Type: {info['type']}")
            report.append(f"  Version: {info['version']}")
            report.append(f"  Size: {size_gb:.2f} GB")
            report.append(f"  Usage Count: {info['usage_count']}")
            report.append(f"  Last Used: {last_used}")
            report.append("")
        
        return "\n".join(report)

def main():
    """Main model management execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge AI Model Manager')
    parser.add_argument('--action', choices=['list', 'verify', 'cleanup', 'report'], 
                      default='report', help='Action to perform')
    parser.add_argument('--model', help='Model name for verify action')
    parser.add_argument('--cleanup-days', type=int, default=30, 
                      help='Days unused for cleanup action')
    
    args = parser.parse_args()
    
    manager = ModelManager()
    
    if args.action == 'list':
        models = manager.list_models()
        print(json.dumps(models, indent=2))
    
    elif args.action == 'verify':
        if not args.model:
            print("--model required for verify action")
            return 1
        
        if manager.verify_model_integrity(args.model):
            print(f"✅ Model {args.model} verified")
            return 0
        else:
            print(f"❌ Model {args.model} verification failed")
            return 1
    
    elif args.action == 'cleanup':
        manager.cleanup_unused_models(args.cleanup_days)
        print(f"✅ Cleanup completed for models unused > {args.cleanup_days} days")
    
    elif args.action == 'report':
        report = manager.generate_model_report()
        print(report)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

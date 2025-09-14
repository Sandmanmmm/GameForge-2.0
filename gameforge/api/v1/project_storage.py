"""
Simple project and asset storage system for AI-generated assets.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class AssetRecord(BaseModel):
    """Asset record for project storage."""
    id: str
    name: str
    type: str
    category: str
    file_path: str
    thumbnail_path: Optional[str] = None
    created_at: datetime
    user_id: str
    job_id: str
    metadata: Dict[str, Any] = {}


class ProjectStorage:
    """Simple file-based project and asset storage."""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.projects_path = self.base_path / "projects"
        self.assets_path = self.base_path / "assets"
        
        # Create directories if they don't exist
        self.projects_path.mkdir(parents=True, exist_ok=True)
        self.assets_path.mkdir(parents=True, exist_ok=True)
    
    def get_user_projects_path(self, user_id: str) -> Path:
        """Get the path for a user's projects."""
        user_path = self.projects_path / user_id
        user_path.mkdir(exist_ok=True)
        return user_path
    
    def get_user_assets_path(self, user_id: str) -> Path:
        """Get the path for a user's assets."""
        user_path = self.assets_path / user_id
        user_path.mkdir(exist_ok=True)
        return user_path
    
    def create_default_project(self, user_id: str) -> str:
        """Create a default project for a user if none exists."""
        user_projects_path = self.get_user_projects_path(user_id)
        default_project_path = user_projects_path / "default.json"
        
        if not default_project_path.exists():
            project_id = f"proj_{uuid.uuid4().hex[:12]}"
            project_data = {
                "id": project_id,
                "name": "My AI Assets",
                "description": "Auto-created project for AI-generated assets",
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "assets": []
            }
            
            with open(default_project_path, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            return project_id
        else:
            with open(default_project_path, 'r') as f:
                project_data = json.load(f)
            return project_data["id"]
    
    def save_asset_to_project(
        self,
        user_id: str,
        asset_url: str,
        job_data: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> AssetRecord:
        """Save an AI-generated asset to a project."""
        if not project_id:
            project_id = self.create_default_project(user_id)
        
        # Create asset record
        asset_id = f"asset_{uuid.uuid4().hex[:12]}"
        asset_record = AssetRecord(
            id=asset_id,
            name=self._generate_asset_name(job_data),
            type=self._determine_asset_type(job_data),
            category=job_data.get("metadata", {}).get("category", "generated"),
            file_path=asset_url,  # For now, use the CDN URL
            created_at=datetime.utcnow(),
            user_id=user_id,
            job_id=job_data["id"],
            metadata={
                "prompt": job_data.get("metadata", {}).get("prompt", ""),
                "style": job_data.get("metadata", {}).get("style", ""),
                "dimensions": job_data.get("metadata", {}).get(
                    "dimensions", ""
                ),
                "quality": job_data.get("metadata", {}).get("quality", ""),
                "ai_generated": True,
                "generation_timestamp": job_data.get("created_at", "")
            }
        )
        
        # Save asset record
        user_assets_path = self.get_user_assets_path(user_id)
        asset_file_path = user_assets_path / f"{asset_id}.json"
        
        with open(asset_file_path, 'w') as f:
            json.dump(asset_record.dict(), f, indent=2, default=str)
        
        # Update project to include this asset
        self._add_asset_to_project(user_id, project_id, asset_record)
        
        return asset_record
    
    def _generate_asset_name(self, job_data: Dict[str, Any]) -> str:
        """Generate a user-friendly name for the asset."""
        metadata = job_data.get("metadata", {})
        prompt = metadata.get("prompt", "")
        category = metadata.get("category", "asset")
        
        # Extract key words from prompt for naming
        if prompt:
            words = prompt.split()[:3]  # Take first 3 words
            base_name = " ".join(words).title()
        else:
            base_name = category.title()
        
        # Add timestamp for uniqueness
        timestamp = datetime.utcnow().strftime("%m%d_%H%M")
        return f"{base_name} {timestamp}"
    
    def _determine_asset_type(self, job_data: Dict[str, Any]) -> str:
        """Determine asset type from job data."""
        metadata = job_data.get("metadata", {})
        category = metadata.get("category", "").lower()
        
        # Map categories to asset types
        type_mapping = {
            "character": "art",
            "environment": "art",
            "weapon": "art",
            "prop": "art",
            "ui": "ui",
            "icon": "ui",
            "texture": "art"
        }
        
        return type_mapping.get(category, "art")
    
    def _add_asset_to_project(
        self,
        user_id: str,
        project_id: str,
        asset_record: AssetRecord
    ) -> None:
        """Add an asset to a project's asset list."""
        user_projects_path = self.get_user_projects_path(user_id)
        
        # Find project file (for now, just use default.json)
        project_file_path = user_projects_path / "default.json"
        
        if project_file_path.exists():
            with open(project_file_path, 'r') as f:
                project_data = json.load(f)
            
            # Add asset to project
            project_data["assets"].append({
                "id": asset_record.id,
                "name": asset_record.name,
                "type": asset_record.type,
                "category": asset_record.category,
                "file_path": asset_record.file_path,
                "created_at": asset_record.created_at.isoformat(),
                "metadata": asset_record.metadata
            })
            
            # Update modified timestamp
            project_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated project
            with open(project_file_path, 'w') as f:
                json.dump(project_data, f, indent=2)
    
    def get_user_assets(self, user_id: str) -> List[AssetRecord]:
        """Get all assets for a user."""
        user_assets_path = self.get_user_assets_path(user_id)
        assets = []
        
        for asset_file in user_assets_path.glob("*.json"):
            try:
                with open(asset_file, 'r') as f:
                    asset_data = json.load(f)
                assets.append(AssetRecord(**asset_data))
            except Exception as e:
                print(f"Error loading asset {asset_file}: {e}")
        
        return sorted(assets, key=lambda x: x.created_at, reverse=True)


# Global storage instance
project_storage = ProjectStorage()
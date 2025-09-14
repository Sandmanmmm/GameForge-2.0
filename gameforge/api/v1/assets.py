"""
Asset management endpoints.

This module handles asset retrieval and management.
For asset generation, use the AI router endpoints in ai.py.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from .auth import get_current_user, UserData
from .project_storage import project_storage


router = APIRouter()


class AssetMetadata(BaseModel):
    """Asset metadata structure."""
    id: str = Field(..., description="Unique asset identifier")
    name: str = Field(..., description="Asset name")
    category: str = Field(..., description="Asset category")
    style: str = Field(..., description="Art style")
    status: str = Field(..., description="Asset status")
    created_at: str = Field(..., description="Creation timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    dimensions: Optional[str] = Field(None, description="Image dimensions")
    tags: List[str] = Field(default_factory=list, description="Asset tags")


class AssetResponse(BaseModel):
    """Response model for asset information."""
    id: str
    name: str
    category: str
    style: str
    status: str
    asset_url: str
    thumbnail_url: Optional[str] = None
    metadata: AssetMetadata

    class Config:
        schema_extra = {
            "example": {
                "id": "asset_123e4567",
                "name": "Mystical Elven Sword",
                "category": "weapons",
                "style": "fantasy",
                "status": "approved",
                "asset_url": "https://cdn.gameforge.ai/assets/sword_001.png",
                "thumbnail_url": "https://cdn.gameforge.ai/thumbs/sword.jpg",
                "metadata": {
                    "id": "asset_123e4567",
                    "name": "Mystical Elven Sword",
                    "category": "weapons",
                    "style": "fantasy",
                    "status": "approved",
                    "created_at": "2025-09-13T10:30:00Z",
                    "file_size": 1024000,
                    "dimensions": "512x512",
                    "tags": ["sword", "elven", "mystical", "weapon"]
                }
            }
        }


@router.get("/", response_model=List[AssetResponse])
async def list_assets(
    category: Optional[str] = None,
    style: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserData = Depends(get_current_user)
):
    """
    List user's assets with optional filtering.
    
    For generating new assets, use POST /api/ai/generate endpoint.
    """
    try:
        # Get user's assets from project storage
        user_assets = project_storage.get_user_assets(current_user.id)
        
        # Apply filters
        filtered_assets = user_assets
        if category:
            filtered_assets = [
                a for a in filtered_assets
                if a.category.lower() == category.lower()
            ]
        if style:
            filtered_assets = [
                a for a in filtered_assets
                if a.metadata.get("style", "").lower() == style.lower()
            ]
        
        # Apply pagination
        paginated_assets = filtered_assets[offset:offset + limit]
        
        # Convert to response format
        response_assets = []
        for asset in paginated_assets:
            response_assets.append(AssetResponse(
                id=asset.id,
                name=asset.name,
                category=asset.category,
                style=asset.metadata.get("style", ""),
                status="approved",  # All AI assets are approved
                asset_url=asset.file_path,
                thumbnail_url=asset.thumbnail_path,
                metadata=AssetMetadata(
                    id=asset.id,
                    name=asset.name,
                    category=asset.category,
                    style=asset.metadata.get("style", ""),
                    status="approved",
                    created_at=asset.created_at.isoformat(),
                    file_size=None,  # Not tracked yet
                    dimensions=asset.metadata.get("dimensions", ""),
                    tags=asset.metadata.get("tags", [])
                )
            ))
        
        return response_assets
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve assets: {str(e)}"
        )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str):
    """
    Get a specific asset by ID.
    
    For asset generation status, use GET /api/ai/job/{job_id} endpoint.
    """
    # TODO: Implement actual asset retrieval from database
    raise HTTPException(status_code=404, detail="Asset not found")


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str):
    """Delete an asset."""
    # TODO: Implement actual asset deletion
    # Should remove from both database and file storage
    return {"message": f"Asset {asset_id} deleted successfully"}


@router.patch("/{asset_id}/metadata")
async def update_asset_metadata(asset_id: str, metadata: AssetMetadata):
    """Update asset metadata."""
    # TODO: Implement metadata updates
    return {"message": f"Asset {asset_id} metadata updated successfully"}


# End of assets module
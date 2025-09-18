"""
Projects API Endpoints for GameForge AI Platform
==============================================

RESTful API endpoints for project management:
- Complete CRUD operations
- Project sharing and collaboration
- Project templates and versioning
- Search and filtering capabilities
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, validator

from gameforge.core.database import get_async_session
from gameforge.models.projects import (
    Project, ProjectStatus, ProjectVisibility, GameEngine, GameGenre
)
from gameforge.models.collaboration import ProjectCollaboration, CollaborationRole
from gameforge.services.collaboration import CollaborationService
from gameforge.core.authorization import (
    get_current_user_auth, UserAuth, Permission, Role,
    RequirePermission, RequireRole, CurrentUser, CurrentUserId
)
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# Create router
projects_router = APIRouter(prefix="/projects", tags=["projects"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ProjectCreate(BaseModel):
    """Request model for creating projects."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=5000, description="Project description")
    summary: Optional[str] = Field(None, max_length=500, description="Short summary for listings")
    engine: Optional[GameEngine] = Field(None, description="Game engine")
    genre: Optional[GameGenre] = Field(None, description="Game genre")
    target_platforms: List[str] = Field(default=[], description="Target platforms")
    visibility: ProjectVisibility = Field(ProjectVisibility.PRIVATE, description="Project visibility")
    is_template: bool = Field(False, description="Whether this is a template project")
    tags: List[str] = Field(default=[], description="Project tags")
    license: Optional[str] = Field(None, description="Project license")
    repository_url: Optional[str] = Field(None, description="Repository URL")
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return [tag.strip().lower() for tag in v if tag.strip()]
    
    @validator('target_platforms')
    def validate_platforms(cls, v):
        valid_platforms = {'windows', 'mac', 'linux', 'web', 'android', 'ios', 'console'}
        return [p for p in v if p.lower() in valid_platforms]


class ProjectUpdate(BaseModel):
    """Request model for updating projects."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    summary: Optional[str] = Field(None, max_length=500)
    engine: Optional[GameEngine] = None
    genre: Optional[GameGenre] = None
    target_platforms: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None
    visibility: Optional[ProjectVisibility] = None
    tags: Optional[List[str]] = None
    license: Optional[str] = None
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is not None and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return [tag.strip().lower() for tag in v if tag.strip()] if v else v


class ProjectResponse(BaseModel):
    """Response model for projects."""
    id: str
    name: str
    slug: str
    description: Optional[str]
    summary: Optional[str]
    engine: Optional[GameEngine]
    genre: Optional[GameGenre]
    target_platforms: List[str]
    status: ProjectStatus
    visibility: ProjectVisibility
    is_featured: bool
    is_template: bool
    owner_id: str
    template_id: Optional[str]
    tags: List[str]
    version: str
    license: Optional[str]
    repository_url: Optional[str]
    demo_url: Optional[str]
    download_url: Optional[str]
    thumbnail_url: Optional[str]
    view_count: int
    download_count: int
    like_count: int
    fork_count: int
    storage_used_bytes: int
    storage_limit_bytes: int
    asset_count: int
    ai_generated_content: bool
    automation_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response model for project listings."""
    id: str
    name: str
    slug: str
    summary: Optional[str]
    engine: Optional[GameEngine]
    genre: Optional[GameGenre]
    status: ProjectStatus
    visibility: ProjectVisibility
    is_featured: bool
    is_template: bool
    owner_id: str
    tags: List[str]
    thumbnail_url: Optional[str]
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectStatsResponse(BaseModel):
    """Response model for project statistics."""
    total_projects: int
    public_projects: int
    private_projects: int
    template_projects: int
    by_status: Dict[str, int]
    by_engine: Dict[str, int]
    by_genre: Dict[str, int]


# ============================================================================
# Helper Functions
# ============================================================================

def get_current_user_id() -> str:
    """Get current user ID from authentication - placeholder implementation."""
    # TODO: Implement actual JWT token validation
    return "550e8400-e29b-41d4-a716-446655440000"  # Placeholder UUID


async def generate_unique_slug(name: str, db: AsyncSession) -> str:
    """Generate a unique slug from project name."""
    base_slug = name.lower().replace(' ', '-').replace('_', '-')
    base_slug = ''.join(c for c in base_slug if c.isalnum() or c == '-')
    
    # Check if slug exists
    counter = 0
    slug = base_slug
    while True:
        result = await db.execute(
            select(Project).where(Project.slug == slug)
        )
        if not result.scalar_one_or_none():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


# ============================================================================
# Project CRUD Endpoints
# ============================================================================

@projects_router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new project."""
    try:
        # Generate unique slug
        slug = await generate_unique_slug(project_data.name, db)
        
        # Create project
        project = Project(
            name=project_data.name,
            slug=slug,
            description=project_data.description,
            summary=project_data.summary,
            engine=project_data.engine,
            genre=project_data.genre,
            target_platforms=project_data.target_platforms,
            visibility=project_data.visibility,
            is_template=project_data.is_template,
            owner_id=current_user_id,
            tags=project_data.tags,
            license=project_data.license,
            repository_url=project_data.repository_url
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Project created: {project.id} by user {current_user_id}")
        return ProjectResponse.from_orm(project)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@projects_router.get("/", response_model=List[ProjectListResponse])
async def list_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    search: Optional[str] = Query(None, description="Search term"),
    status_filter: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    engine_filter: Optional[GameEngine] = Query(None, description="Filter by engine"),
    genre_filter: Optional[GameGenre] = Query(None, description="Filter by genre"),
    visibility_filter: Optional[ProjectVisibility] = Query(None, description="Filter by visibility"),
    owner_only: bool = Query(False, description="Show only projects owned by current user"),
    templates_only: bool = Query(False, description="Show only template projects"),
    featured_only: bool = Query(False, description="Show only featured projects"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """List projects with filtering and pagination."""
    try:
        # Build query
        query = select(Project)
        
        # Apply filters
        filters = []
        
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.summary.ilike(search_term),
                    Project.tags.op('&&')(func.array([search.lower()]))
                )
            )
        
        if status_filter:
            filters.append(Project.status == status_filter)
            
        if engine_filter:
            filters.append(Project.engine == engine_filter)
            
        if genre_filter:
            filters.append(Project.genre == genre_filter)
            
        if visibility_filter:
            filters.append(Project.visibility == visibility_filter)
        elif not owner_only:
            # Non-owners can only see public projects unless specifically requesting own
            filters.append(
                or_(
                    Project.visibility == ProjectVisibility.PUBLIC,
                    Project.owner_id == current_user_id
                )
            )
            
        if owner_only:
            filters.append(Project.owner_id == current_user_id)
            
        if templates_only:
            filters.append(Project.is_template == True)
            
        if featured_only:
            filters.append(Project.is_featured == True)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply sorting
        if sort_order.lower() == "desc":
            if sort_by == "name":
                query = query.order_by(desc(Project.name))
            elif sort_by == "updated_at":
                query = query.order_by(desc(Project.updated_at))
            elif sort_by == "view_count":
                query = query.order_by(desc(Project.view_count))
            elif sort_by == "like_count":
                query = query.order_by(desc(Project.like_count))
            else:
                query = query.order_by(desc(Project.created_at))
        else:
            if sort_by == "name":
                query = query.order_by(Project.name)
            elif sort_by == "updated_at":
                query = query.order_by(Project.updated_at)
            elif sort_by == "view_count":
                query = query.order_by(Project.view_count)
            elif sort_by == "like_count":
                query = query.order_by(Project.like_count)
            else:
                query = query.order_by(Project.created_at)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [ProjectListResponse.from_orm(project) for project in projects]
        
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@projects_router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str = Path(..., description="Project ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific project by ID."""
    try:
        # Get project with collaborations
        query = select(Project).options(
            selectinload(Project.collaborations)
        ).where(Project.id == project_id)
        
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access permissions
        collaboration_service = CollaborationService(db)
        if not await collaboration_service.can_user_access_project(project_id, current_user_id):
            if project.visibility != ProjectVisibility.PUBLIC:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this project"
                )
        
        # Increment view count if not owner
        if project.owner_id != current_user_id:
            project.view_count += 1
            await db.commit()
        
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@projects_router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str = Path(..., description="Project ID"),
    project_data: ProjectUpdate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Update a project."""
    try:
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check permissions - only owner or admin collaborators can update
        collaboration_service = CollaborationService(db)
        user_role = await collaboration_service.get_user_role_in_project(project_id, current_user_id)
        
        if (project.owner_id != current_user_id and 
            user_role not in [CollaborationRole.ADMIN, CollaborationRole.OWNER]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update this project"
            )
        
        # Update fields
        update_data = project_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(project, field):
                setattr(project, field, value)
        
        # Update slug if name changed
        if 'name' in update_data:
            project.slug = await generate_unique_slug(project.name, db)
        
        project.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(project)
        
        logger.info(f"Project updated: {project_id} by user {current_user_id}")
        return ProjectResponse.from_orm(project)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@projects_router.delete("/{project_id}")
async def delete_project(
    project_id: str = Path(..., description="Project ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a project (only owners can delete)."""
    try:
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Only owner can delete
        if project.owner_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners can delete projects"
            )
        
        # Delete project (cascade will handle related records)
        await db.delete(project)
        await db.commit()
        
        logger.info(f"Project deleted: {project_id} by user {current_user_id}")
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


# ============================================================================
# Project Statistics and Analytics
# ============================================================================

@projects_router.get("/stats/overview", response_model=ProjectStatsResponse)
async def get_project_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get project statistics overview."""
    try:
        # Total projects (public + user's private)
        total_query = select(func.count(Project.id)).where(
            or_(
                Project.visibility == ProjectVisibility.PUBLIC,
                Project.owner_id == current_user_id
            )
        )
        total_result = await db.execute(total_query)
        total_projects = total_result.scalar()
        
        # Public projects
        public_query = select(func.count(Project.id)).where(
            Project.visibility == ProjectVisibility.PUBLIC
        )
        public_result = await db.execute(public_query)
        public_projects = public_result.scalar()
        
        # Private projects for user
        private_query = select(func.count(Project.id)).where(
            and_(
                Project.owner_id == current_user_id,
                Project.visibility == ProjectVisibility.PRIVATE
            )
        )
        private_result = await db.execute(private_query)
        private_projects = private_result.scalar()
        
        # Template projects
        template_query = select(func.count(Project.id)).where(
            and_(
                Project.is_template == True,
                or_(
                    Project.visibility == ProjectVisibility.PUBLIC,
                    Project.owner_id == current_user_id
                )
            )
        )
        template_result = await db.execute(template_query)
        template_projects = template_result.scalar()
        
        # Stats by status
        status_query = select(
            Project.status,
            func.count(Project.id)
        ).where(
            or_(
                Project.visibility == ProjectVisibility.PUBLIC,
                Project.owner_id == current_user_id
            )
        ).group_by(Project.status)
        
        status_result = await db.execute(status_query)
        by_status = {str(row[0]): row[1] for row in status_result.fetchall()}
        
        # Stats by engine
        engine_query = select(
            Project.engine,
            func.count(Project.id)
        ).where(
            and_(
                Project.engine.is_not(None),
                or_(
                    Project.visibility == ProjectVisibility.PUBLIC,
                    Project.owner_id == current_user_id
                )
            )
        ).group_by(Project.engine)
        
        engine_result = await db.execute(engine_query)
        by_engine = {str(row[0]): row[1] for row in engine_result.fetchall()}
        
        # Stats by genre
        genre_query = select(
            Project.genre,
            func.count(Project.id)
        ).where(
            and_(
                Project.genre.is_not(None),
                or_(
                    Project.visibility == ProjectVisibility.PUBLIC,
                    Project.owner_id == current_user_id
                )
            )
        ).group_by(Project.genre)
        
        genre_result = await db.execute(genre_query)
        by_genre = {str(row[0]): row[1] for row in genre_result.fetchall()}
        
        return ProjectStatsResponse(
            total_projects=total_projects or 0,
            public_projects=public_projects or 0,
            private_projects=private_projects or 0,
            template_projects=template_projects or 0,
            by_status=by_status,
            by_engine=by_engine,
            by_genre=by_genre
        )
        
    except Exception as e:
        logger.error(f"Error getting project stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project statistics: {str(e)}"
        )


# ============================================================================
# Project Actions
# ============================================================================

@projects_router.post("/{project_id}/fork", response_model=ProjectResponse)
async def fork_project(
    project_id: str = Path(..., description="Project ID to fork"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Fork a project to create a copy."""
    try:
        # Get original project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        original_project = result.scalar_one_or_none()
        
        if not original_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if project can be forked (must be public or user has access)
        collaboration_service = CollaborationService(db)
        if (original_project.visibility != ProjectVisibility.PUBLIC and
            not await collaboration_service.can_user_access_project(project_id, current_user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot fork this project - access denied"
            )
        
        # Create forked project
        fork_name = f"{original_project.name} (Fork)"
        fork_slug = await generate_unique_slug(fork_name, db)
        
        forked_project = Project(
            name=fork_name,
            slug=fork_slug,
            description=original_project.description,
            summary=original_project.summary,
            engine=original_project.engine,
            genre=original_project.genre,
            target_platforms=original_project.target_platforms.copy(),
            visibility=ProjectVisibility.PRIVATE,  # Forks start as private
            owner_id=current_user_id,
            template_id=original_project.template_id,
            tags=original_project.tags.copy(),
            license=original_project.license,
            ai_generated_content=original_project.ai_generated_content
        )
        
        db.add(forked_project)
        
        # Update fork count on original
        original_project.fork_count += 1
        
        await db.commit()
        await db.refresh(forked_project)
        
        logger.info(f"Project forked: {project_id} -> {forked_project.id} by user {current_user_id}")
        return ProjectResponse.from_orm(forked_project)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error forking project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fork project: {str(e)}"
        )


@projects_router.post("/{project_id}/like")
async def like_project(
    project_id: str = Path(..., description="Project ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Like/unlike a project."""
    try:
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access
        collaboration_service = CollaborationService(db)
        if (project.visibility != ProjectVisibility.PUBLIC and
            not await collaboration_service.can_user_access_project(project_id, current_user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot like this project - access denied"
            )
        
        # Toggle like (in a real implementation, you'd track individual likes)
        # For now, just increment the counter
        project.like_count += 1
        await db.commit()
        
        return {"message": "Project liked successfully", "like_count": project.like_count}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error liking project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like project: {str(e)}"
        )

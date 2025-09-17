"""
API Endpoints for Project Collaboration Features
===============================================

RESTful API endpoints providing:
- Project collaboration management
- Team member management
- Invitation system
- Activity feeds
- Comments and notifications
- Real-time WebSocket endpoints
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from gameforge.core.database import get_db
from gameforge.models.collaboration import (
    ProjectRole, ActivityType, NotificationType, InviteStatus,
    Project, ProjectCollaboration, ProjectInvite, ActivityLog, Comment, Notification
)
from gameforge.services.collaboration import (
    CollaborationService, CommentService, NotificationService
)
from gameforge.services.realtime import (
    connection_manager, RealTimeCollaborationService
)
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# Create router
collaboration_router = APIRouter(prefix="/api/v1/collaboration", tags=["collaboration"])


# Pydantic Models for API Requests/Responses
class ProjectCollaborationCreate(BaseModel):
    """Request model for adding collaborators."""
    email: str = Field(..., description="Email of user to invite")
    role: ProjectRole = Field(..., description="Role to assign")
    custom_message: Optional[str] = Field(None, description="Custom invitation message")


class ProjectCollaborationUpdate(BaseModel):
    """Request model for updating collaborator roles."""
    role: ProjectRole = Field(..., description="New role to assign")


class CommentCreate(BaseModel):
    """Request model for creating comments."""
    content: str = Field(..., min_length=1, max_length=5000, description="Comment content")
    entity_type: Optional[str] = Field(None, description="Type of entity being commented on")
    entity_id: Optional[str] = Field(None, description="ID of entity being commented on")
    parent_id: Optional[str] = Field(None, description="Parent comment ID for threading")


class CommentUpdate(BaseModel):
    """Request model for updating comments."""
    content: str = Field(..., min_length=1, max_length=5000, description="Updated comment content")


class NotificationUpdate(BaseModel):
    """Request model for updating notifications."""
    is_read: bool = Field(..., description="Mark as read/unread")


class ActivityLogResponse(BaseModel):
    """Response model for activity log entries."""
    id: str
    type: ActivityType
    description: str
    user_id: str
    project_id: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Response model for comments."""
    id: str
    content: str
    user_id: str
    project_id: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    parent_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Response model for notifications."""
    id: str
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    entity_type: Optional[str]
    entity_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCollaborationResponse(BaseModel):
    """Response model for project collaborations."""
    id: str
    user_id: str
    project_id: str
    role: ProjectRole
    joined_at: datetime

    class Config:
        from_attributes = True


class ProjectInviteResponse(BaseModel):
    """Response model for project invites."""
    id: str
    project_id: str
    email: str
    role: ProjectRole
    status: InviteStatus
    invited_by: str
    custom_message: Optional[str]
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Helper function to get current user (placeholder - integrate with your auth system)
async def get_current_user_id() -> str:
    """Get current authenticated user ID."""
    # TODO: Integrate with actual authentication system
    return "user_123"  # Placeholder


# Project Collaboration Endpoints
@collaboration_router.get("/projects/{project_id}/collaborators", response_model=List[ProjectCollaborationResponse])
async def get_project_collaborators(
    project_id: str = Path(..., description="Project ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all collaborators for a project."""
    service = CollaborationService(db)
    
    # Check if user has access to this project
    if not await service.check_project_access(project_id, current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    collaborators = await service.get_project_collaborators(project_id)
    return [ProjectCollaborationResponse.from_orm(collab) for collab in collaborators]


@collaboration_router.post("/projects/{project_id}/collaborators", response_model=ProjectInviteResponse)
async def invite_collaborator(
    project_id: str = Path(..., description="Project ID"),
    request: ProjectCollaborationCreate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Invite a new collaborator to a project."""
    service = CollaborationService(db)
    
    # Check if user can invite others (must be owner or admin)
    if not await service.check_collaboration_permission(project_id, current_user_id, [ProjectRole.OWNER, ProjectRole.ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite collaborators"
        )
    
    try:
        invite = await service.invite_user(
            project_id=project_id,
            email=request.email,
            role=request.role,
            invited_by=current_user_id,
            custom_message=request.custom_message
        )
        
        # Broadcast collaboration event
        realtime_service = RealTimeCollaborationService(db)
        await realtime_service.handle_collaboration_event(
            project_id=project_id,
            user_id=current_user_id,
            event_type="invited",
            metadata={"email": request.email, "role": request.role.value}
        )
        
        return ProjectInviteResponse.from_orm(invite)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@collaboration_router.put("/projects/{project_id}/collaborators/{user_id}", response_model=ProjectCollaborationResponse)
async def update_collaborator_role(
    project_id: str = Path(..., description="Project ID"),
    user_id: str = Path(..., description="User ID of collaborator"),
    request: ProjectCollaborationUpdate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a collaborator's role."""
    service = CollaborationService(db)
    
    # Check permissions
    if not await service.check_collaboration_permission(project_id, current_user_id, [ProjectRole.OWNER, ProjectRole.ADMIN]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update collaborator roles"
        )
    
    try:
        collaboration = await service.update_collaboration_role(
            project_id=project_id,
            user_id=user_id,
            new_role=request.role
        )
        
        # Broadcast collaboration event
        realtime_service = RealTimeCollaborationService(db)
        await realtime_service.handle_collaboration_event(
            project_id=project_id,
            user_id=current_user_id,
            event_type="role_changed",
            target_user_id=user_id,
            metadata={"new_role": request.role.value}
        )
        
        return ProjectCollaborationResponse.from_orm(collaboration)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@collaboration_router.delete("/projects/{project_id}/collaborators/{user_id}")
async def remove_collaborator(
    project_id: str = Path(..., description="Project ID"),
    user_id: str = Path(..., description="User ID of collaborator"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Remove a collaborator from a project."""
    service = CollaborationService(db)
    
    # Check permissions (owner can remove anyone, admin can remove non-owners, users can remove themselves)
    user_role = await service.get_user_role(project_id, current_user_id)
    target_role = await service.get_user_role(project_id, user_id)
    
    can_remove = (
        user_role == ProjectRole.OWNER or
        (user_role == ProjectRole.ADMIN and target_role != ProjectRole.OWNER) or
        current_user_id == user_id
    )
    
    if not can_remove:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to remove this collaborator"
        )
    
    try:
        await service.remove_collaboration(project_id, user_id)
        
        # Broadcast collaboration event
        realtime_service = RealTimeCollaborationService(db)
        await realtime_service.handle_collaboration_event(
            project_id=project_id,
            user_id=current_user_id,
            event_type="left",
            target_user_id=user_id if current_user_id != user_id else None
        )
        
        return {"message": "Collaborator removed successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Invitation Management Endpoints
@collaboration_router.get("/invites", response_model=List[ProjectInviteResponse])
async def get_user_invites(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending invites for the current user."""
    service = CollaborationService(db)
    
    # Get user's email (this would come from user service in real implementation)
    user_email = f"user_{current_user_id}@example.com"  # Placeholder
    
    invites = await service.get_user_invites(user_email)
    return [ProjectInviteResponse.from_orm(invite) for invite in invites]


@collaboration_router.post("/invites/{invite_id}/accept")
async def accept_invite(
    invite_id: str = Path(..., description="Invite ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Accept a project invitation."""
    service = CollaborationService(db)
    
    try:
        collaboration = await service.accept_invite(invite_id, current_user_id)
        
        # Broadcast collaboration event
        realtime_service = RealTimeCollaborationService(db)
        await realtime_service.handle_collaboration_event(
            project_id=collaboration.project_id,
            user_id=current_user_id,
            event_type="joined"
        )
        
        return {"message": "Invitation accepted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@collaboration_router.post("/invites/{invite_id}/decline")
async def decline_invite(
    invite_id: str = Path(..., description="Invite ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Decline a project invitation."""
    service = CollaborationService(db)
    
    try:
        await service.decline_invite(invite_id)
        return {"message": "Invitation declined"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Activity Feed Endpoints
@collaboration_router.get("/projects/{project_id}/activity", response_model=List[ActivityLogResponse])
async def get_project_activity(
    project_id: str = Path(..., description="Project ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get activity feed for a project."""
    service = CollaborationService(db)
    
    # Check access
    if not await service.check_project_access(project_id, current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    activities = await service.get_project_activity(project_id, limit=limit, offset=offset)
    return [ActivityLogResponse.from_orm(activity) for activity in activities]


# Comment Endpoints
@collaboration_router.get("/projects/{project_id}/comments", response_model=List[CommentResponse])
async def get_project_comments(
    project_id: str = Path(..., description="Project ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of comments to return"),
    offset: int = Query(0, ge=0, description="Number of comments to skip"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get comments for a project or specific entity."""
    collaboration_service = CollaborationService(db)
    comment_service = CommentService(db)
    
    # Check access
    if not await collaboration_service.check_project_access(project_id, current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    comments = await comment_service.get_comments(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset
    )
    return [CommentResponse.from_orm(comment) for comment in comments]


@collaboration_router.post("/projects/{project_id}/comments", response_model=CommentResponse)
async def create_comment(
    project_id: str = Path(..., description="Project ID"),
    request: CommentCreate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new comment."""
    collaboration_service = CollaborationService(db)
    comment_service = CommentService(db)
    
    # Check access
    if not await collaboration_service.check_project_access(project_id, current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    comment = await comment_service.create_comment(
        user_id=current_user_id,
        project_id=project_id,
        content=request.content,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        parent_id=request.parent_id
    )
    
    # Broadcast comment event
    realtime_service = RealTimeCollaborationService(db)
    await realtime_service.handle_comment_event(
        project_id=project_id,
        comment_id=comment.id,
        user_id=current_user_id,
        content=request.content,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        parent_id=request.parent_id
    )
    
    return CommentResponse.from_orm(comment)


@collaboration_router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str = Path(..., description="Comment ID"),
    request: CommentUpdate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a comment."""
    comment_service = CommentService(db)
    
    try:
        comment = await comment_service.update_comment(
            comment_id=comment_id,
            user_id=current_user_id,
            content=request.content
        )
        return CommentResponse.from_orm(comment)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@collaboration_router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str = Path(..., description="Comment ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment."""
    comment_service = CommentService(db)
    
    try:
        await comment_service.delete_comment(comment_id, current_user_id)
        return {"message": "Comment deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# Notification Endpoints
@collaboration_router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current user."""
    service = NotificationService(db)
    
    notifications = await service.get_user_notifications(
        user_id=current_user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only
    )
    return [NotificationResponse.from_orm(notification) for notification in notifications]


@collaboration_router.put("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str = Path(..., description="Notification ID"),
    request: NotificationUpdate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a notification (mark as read/unread)."""
    service = NotificationService(db)
    
    try:
        notification = await service.update_notification(
            notification_id=notification_id,
            user_id=current_user_id,
            is_read=request.is_read
        )
        return NotificationResponse.from_orm(notification)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@collaboration_router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    service = NotificationService(db)
    
    count = await service.mark_all_read(current_user_id)
    return {"message": f"Marked {count} notifications as read"}


# WebSocket Endpoint for Real-time Collaboration
@collaboration_router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str = Path(..., description="Project ID"),
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time collaboration."""
    collaboration_service = CollaborationService(db)
    
    # Verify user has access to the project
    if not await collaboration_service.check_project_access(project_id, user_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    connection_id = str(uuid.uuid4())
    
    try:
        # Connect to the project
        await connection_manager.connect(websocket, user_id, connection_id, project_id)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Handle ping/pong for connection health
                    await connection_manager.send_personal_message(user_id, connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "activity":
                    # Update user presence
                    await connection_manager.update_user_presence(user_id, project_id)
                
                # Add more message type handlers as needed
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    user_id=user_id,
                    project_id=project_id,
                    error=str(e)
                )
                break
                
    finally:
        # Clean up connection
        await connection_manager.disconnect(user_id, connection_id)


# Export router
__all__ = ['collaboration_router']
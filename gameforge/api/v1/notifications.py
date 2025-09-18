"""
Notifications API Endpoints for GameForge AI Platform
===================================================

RESTful API endpoints for notification management:
- CRUD operations for notifications
- Real-time WebSocket notifications
- Bulk operations (mark all read, delete multiple)
- Notification preferences and settings
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update, delete
from pydantic import BaseModel, Field, field_validator

from gameforge.core.database import get_async_session
from gameforge.models.collaboration import Notification, NotificationType
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# Create router
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class NotificationConnectionManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket for a user."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_notification(self, user_id: str, notification_data: dict):
        """Send notification to all user's connected WebSockets."""
        if user_id in self.active_connections:
            disconnected_sockets = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(notification_data)
                except:
                    disconnected_sockets.append(websocket)
            
            # Clean up disconnected sockets
            for websocket in disconnected_sockets:
                self.disconnect(websocket, user_id)


# Global connection manager
notification_manager = NotificationConnectionManager()


# ============================================================================
# Pydantic Models
# ============================================================================

class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    entity_type: Optional[str] = Field(None, description="Related entity type")
    entity_id: Optional[str] = Field(None, description="Related entity ID")
    action_url: Optional[str] = Field(None, description="Action URL")
    action_text: Optional[str] = Field(None, max_length=100, description="Action button text")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class NotificationResponse(BaseModel):
    """Response model for notifications."""
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    action_url: Optional[str]
    action_text: Optional[str]
    invite_metadata: Dict[str, Any]
    read_at: Optional[datetime]
    archived_at: Optional[datetime]
    created_at: datetime
    is_read: bool
    is_archived: bool
    
    class Config:
        from_attributes = True
    
    @property
    def is_read(self) -> bool:
        return self.read_at is not None
    
    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class NotificationUpdate(BaseModel):
    """Request model for updating notifications."""
    read: Optional[bool] = Field(None, description="Mark as read/unread")
    archived: Optional[bool] = Field(None, description="Archive/unarchive notification")


class NotificationStats(BaseModel):
    """Response model for notification statistics."""
    total_count: int
    unread_count: int
    archived_count: int
    by_type: Dict[str, int]
    recent_count: int  # Last 24 hours


class BulkNotificationUpdate(BaseModel):
    """Request model for bulk notification operations."""
    notification_ids: List[str] = Field(..., description="List of notification IDs")
    action: str = Field(..., description="Action to perform")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['mark_read', 'mark_unread', 'archive', 'unarchive', 'delete']:
            raise ValueError('action must be one of: mark_read, mark_unread, archive, unarchive, delete')
        return v


# ============================================================================
# Helper Functions
# ============================================================================

def get_current_user_id() -> str:
    """Get current user ID from authentication - placeholder implementation."""
    # TODO: Implement actual JWT token validation
    return "550e8400-e29b-41d4-a716-446655440000"  # Placeholder UUID


# ============================================================================
# Notification CRUD Endpoints
# ============================================================================

@notifications_router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    include_archived: bool = Query(False, description="Include archived notifications"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """List user notifications with filtering."""
    try:
        # Build query
        query = select(Notification).where(Notification.user_id == current_user_id)
        
        # Apply filters
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        
        if notification_type:
            query = query.where(Notification.type == notification_type)
        
        if entity_type:
            query = query.where(Notification.entity_type == entity_type)
        
        if not include_archived:
            query = query.where(Notification.archived_at.is_(None))
        
        # Order by creation date (newest first)
        query = query.order_by(desc(Notification.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return [NotificationResponse.from_orm(notification) for notification in notifications]
        
    except Exception as e:
        logger.error(f"Error listing notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list notifications: {str(e)}"
        )


@notifications_router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    target_user_id: str = Query(..., description="Target user ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new notification for a specific user."""
    try:
        # Create notification
        notification = Notification(
            user_id=target_user_id,
            type=notification_data.type,
            title=notification_data.title,
            message=notification_data.message,
            entity_type=notification_data.entity_type,
            entity_id=notification_data.entity_id,
            action_url=notification_data.action_url,
            action_text=notification_data.action_text,
            invite_metadata=notification_data.metadata or {}
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        # Send real-time notification via WebSocket
        notification_response = NotificationResponse.from_orm(notification)
        await notification_manager.send_notification(
            target_user_id, 
            {
                "type": "new_notification",
                "notification": notification_response.dict()
            }
        )
        
        logger.info(f"Notification created: {notification.id} for user {target_user_id}")
        return notification_response
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@notifications_router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str = Path(..., description="Notification ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific notification."""
    try:
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return NotificationResponse.from_orm(notification)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification: {str(e)}"
        )


@notifications_router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str = Path(..., description="Notification ID"),
    notification_data: NotificationUpdate = ...,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Update a notification (mark as read/unread, archive/unarchive)."""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Update fields
        if notification_data.read is not None:
            if notification_data.read:
                notification.read_at = datetime.utcnow()
            else:
                notification.read_at = None
        
        if notification_data.archived is not None:
            if notification_data.archived:
                notification.archived_at = datetime.utcnow()
            else:
                notification.archived_at = None
        
        await db.commit()
        await db.refresh(notification)
        
        logger.info(f"Notification updated: {notification_id}")
        return NotificationResponse.from_orm(notification)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification: {str(e)}"
        )


@notifications_router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str = Path(..., description="Notification ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a notification."""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Delete notification
        await db.delete(notification)
        await db.commit()
        
        logger.info(f"Notification deleted: {notification_id}")
        return {"message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


# ============================================================================
# Bulk Operations
# ============================================================================

@notifications_router.put("/bulk")
async def bulk_update_notifications(
    bulk_data: BulkNotificationUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Perform bulk operations on notifications."""
    try:
        # Build base query for user's notifications
        base_query = select(Notification).where(
            and_(
                Notification.user_id == current_user_id,
                Notification.id.in_(bulk_data.notification_ids)
            )
        )
        
        if bulk_data.action == "delete":
            # Delete notifications
            delete_query = delete(Notification).where(
                and_(
                    Notification.user_id == current_user_id,
                    Notification.id.in_(bulk_data.notification_ids)
                )
            )
            result = await db.execute(delete_query)
            affected_count = result.rowcount
        else:
            # Update notifications
            update_values = {}
            
            if bulk_data.action == "mark_read":
                update_values = {Notification.read_at: datetime.utcnow()}
            elif bulk_data.action == "mark_unread":
                update_values = {Notification.read_at: None}
            elif bulk_data.action == "archive":
                update_values = {Notification.archived_at: datetime.utcnow()}
            elif bulk_data.action == "unarchive":
                update_values = {Notification.archived_at: None}
            
            update_query = update(Notification).where(
                and_(
                    Notification.user_id == current_user_id,
                    Notification.id.in_(bulk_data.notification_ids)
                )
            ).values(**update_values)
            
            result = await db.execute(update_query)
            affected_count = result.rowcount
        
        await db.commit()
        
        logger.info(f"Bulk operation {bulk_data.action} performed on {affected_count} notifications")
        return {
            "message": f"Bulk operation completed",
            "action": bulk_data.action,
            "affected_count": affected_count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error performing bulk operation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk operation: {str(e)}"
        )


@notifications_router.put("/mark-all-read")
async def mark_all_read(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Mark all notifications as read."""
    try:
        update_query = update(Notification).where(
            and_(
                Notification.user_id == current_user_id,
                Notification.read_at.is_(None)
            )
        ).values(read_at=datetime.utcnow())
        
        result = await db.execute(update_query)
        affected_count = result.rowcount
        
        await db.commit()
        
        logger.info(f"Marked {affected_count} notifications as read for user {current_user_id}")
        return {
            "message": "All notifications marked as read",
            "affected_count": affected_count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


# ============================================================================
# Statistics and Analytics
# ============================================================================

@notifications_router.get("/stats/overview", response_model=NotificationStats)
async def get_notification_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get notification statistics for the current user."""
    try:
        # Total count
        total_query = select(func.count(Notification.id)).where(
            Notification.user_id == current_user_id
        )
        total_result = await db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # Unread count
        unread_query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user_id,
                Notification.read_at.is_(None)
            )
        )
        unread_result = await db.execute(unread_query)
        unread_count = unread_result.scalar() or 0
        
        # Archived count
        archived_query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user_id,
                Notification.archived_at.is_not(None)
            )
        )
        archived_result = await db.execute(archived_query)
        archived_count = archived_result.scalar() or 0
        
        # Recent count (last 24 hours)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user_id,
                Notification.created_at >= twenty_four_hours_ago
            )
        )
        recent_result = await db.execute(recent_query)
        recent_count = recent_result.scalar() or 0
        
        # By type
        type_query = select(
            Notification.type,
            func.count(Notification.id)
        ).where(
            Notification.user_id == current_user_id
        ).group_by(Notification.type)
        
        type_result = await db.execute(type_query)
        by_type = {str(row[0]): row[1] for row in type_result.fetchall()}
        
        return NotificationStats(
            total_count=total_count,
            unread_count=unread_count,
            archived_count=archived_count,
            by_type=by_type,
            recent_count=recent_count
        )
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification statistics: {str(e)}"
        )


# ============================================================================
# WebSocket Endpoint for Real-time Notifications
# ============================================================================

@notifications_router.websocket("/ws")
async def notification_websocket(
    websocket: WebSocket,
    current_user_id: str = Query(..., description="User ID")
):
    """WebSocket endpoint for real-time notifications."""
    await notification_manager.connect(websocket, current_user_id)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            message = await websocket.receive_text()
            
            # Handle ping/pong for connection health
            if message == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, current_user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {current_user_id}: {str(e)}")
        notification_manager.disconnect(websocket, current_user_id)

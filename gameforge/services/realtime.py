"""
Real-time Collaboration Infrastructure for GameForge AI Platform
================================================================

WebSocket-based real-time collaboration system providing:
- Live project updates and notifications
- Real-time activity feeds
- User presence tracking
- Live comment threads
- Asset synchronization
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from gameforge.core.logging_config import get_structured_logger
from gameforge.services.collaboration import CollaborationService, NotificationService
from gameforge.models.collaboration import ActivityType, NotificationType

logger = get_structured_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time collaboration."""
    
    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        
        # Project subscriptions: {project_id: {user_id: set of connection_ids}}
        self.project_subscriptions: Dict[str, Dict[str, Set[str]]] = {}
        
        # User presence: {project_id: {user_id: last_activity}}
        self.user_presence: Dict[str, Dict[str, datetime]] = {}
        
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str,
        project_id: Optional[str] = None
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        # Store connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_id] = websocket
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "project_id": project_id,
            "connected_at": datetime.utcnow()
        }
        
        # Subscribe to project if specified
        if project_id:
            await self.subscribe_to_project(user_id, connection_id, project_id)
        
        logger.info(
            "WebSocket connection established",
            user_id=user_id,
            connection_id=connection_id,
            project_id=project_id
        )
        
        # Send welcome message
        await self.send_personal_message(user_id, connection_id, {
            "type": "connection_established",
            "message": "Connected to GameForge real-time collaboration",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def disconnect(self, user_id: str, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        # Remove from active connections
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(connection_id, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Get metadata before removal
        metadata = self.connection_metadata.get(connection_id, {})
        project_id = metadata.get("project_id")
        
        # Remove from project subscriptions
        if project_id and project_id in self.project_subscriptions:
            if user_id in self.project_subscriptions[project_id]:
                self.project_subscriptions[project_id][user_id].discard(connection_id)
                if not self.project_subscriptions[project_id][user_id]:
                    del self.project_subscriptions[project_id][user_id]
                    
                    # Update user presence
                    if project_id in self.user_presence:
                        self.user_presence[project_id].pop(user_id, None)
                        
                        # Broadcast user left
                        await self.broadcast_to_project(project_id, {
                            "type": "user_left",
                            "user_id": user_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }, exclude_user=user_id)
        
        # Clean up metadata
        self.connection_metadata.pop(connection_id, None)
        
        logger.info(
            "WebSocket connection closed",
            user_id=user_id,
            connection_id=connection_id,
            project_id=project_id
        )
    
    async def subscribe_to_project(
        self,
        user_id: str,
        connection_id: str,
        project_id: str
    ) -> None:
        """Subscribe a connection to project updates."""
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = {}
        
        if user_id not in self.project_subscriptions[project_id]:
            self.project_subscriptions[project_id][user_id] = set()
        
        self.project_subscriptions[project_id][user_id].add(connection_id)
        
        # Update user presence
        if project_id not in self.user_presence:
            self.user_presence[project_id] = {}
        self.user_presence[project_id][user_id] = datetime.utcnow()
        
        # Broadcast user joined
        await self.broadcast_to_project(project_id, {
            "type": "user_joined",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)
        
        # Send current online users to the new subscriber
        online_users = list(self.user_presence[project_id].keys())
        await self.send_personal_message(user_id, connection_id, {
            "type": "online_users",
            "users": online_users,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_personal_message(
        self,
        user_id: str,
        connection_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Send message to a specific connection."""
        if (user_id in self.active_connections and 
            connection_id in self.active_connections[user_id]):
            
            websocket = self.active_connections[user_id][connection_id]
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(
                    "Failed to send message to connection",
                    user_id=user_id,
                    connection_id=connection_id,
                    error=str(e)
                )
                # Clean up broken connection
                await self.disconnect(user_id, connection_id)
    
    async def send_to_user(
        self,
        user_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Send message to all connections of a user."""
        if user_id in self.active_connections:
            for connection_id in list(self.active_connections[user_id].keys()):
                await self.send_personal_message(user_id, connection_id, message)
    
    async def broadcast_to_project(
        self,
        project_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ) -> None:
        """Broadcast message to all users subscribed to a project."""
        if project_id not in self.project_subscriptions:
            return
        
        for user_id, connection_ids in self.project_subscriptions[project_id].items():
            if exclude_user and user_id == exclude_user:
                continue
                
            for connection_id in list(connection_ids):
                await self.send_personal_message(user_id, connection_id, message)
    
    async def update_user_presence(
        self,
        user_id: str,
        project_id: str
    ) -> None:
        """Update user's last activity timestamp."""
        if project_id in self.user_presence:
            self.user_presence[project_id][user_id] = datetime.utcnow()
    
    def get_online_users(self, project_id: str) -> List[str]:
        """Get list of users currently online in a project."""
        if project_id not in self.user_presence:
            return []
        
        # Filter out users who haven't been active recently (5 minutes)
        cutoff = datetime.utcnow().timestamp() - 300  # 5 minutes
        active_users = []
        
        for user_id, last_activity in self.user_presence[project_id].items():
            if last_activity.timestamp() > cutoff:
                active_users.append(user_id)
        
        return active_users


# Global connection manager instance
connection_manager = ConnectionManager()


class RealTimeCollaborationService:
    """Service for handling real-time collaboration events."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.collaboration_service = CollaborationService(db_session)
        self.notification_service = NotificationService(db_session)
    
    async def handle_activity_event(
        self,
        activity_type: ActivityType,
        project_id: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle and broadcast activity events."""
        # Log the activity
        activity = await self.collaboration_service.log_activity(
            activity_type=activity_type,
            description=description,
            project_id=project_id,
            user_id=user_id,
            metadata=metadata
        )
        
        # Broadcast to project subscribers
        await connection_manager.broadcast_to_project(project_id, {
            "type": "activity_update",
            "activity": {
                "id": activity.id,
                "type": activity_type.value,
                "description": description,
                "user_id": user_id,
                "metadata": metadata or {},
                "timestamp": activity.created_at.isoformat()
            }
        })
        
        # Update user presence
        await connection_manager.update_user_presence(user_id, project_id)
    
    async def handle_comment_event(
        self,
        project_id: str,
        comment_id: str,
        user_id: str,
        content: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> None:
        """Handle and broadcast comment events."""
        # Broadcast new comment to project subscribers
        await connection_manager.broadcast_to_project(project_id, {
            "type": "new_comment",
            "comment": {
                "id": comment_id,
                "user_id": user_id,
                "content": content,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "parent_id": parent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Create notifications for mentioned users (if any)
        # This would require parsing @mentions in the content
        
        # Update user presence
        await connection_manager.update_user_presence(user_id, project_id)
    
    async def handle_asset_event(
        self,
        project_id: str,
        asset_id: str,
        user_id: str,
        event_type: str,  # 'created', 'updated', 'deleted'
        asset_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle and broadcast asset events."""
        # Broadcast asset update to project subscribers
        await connection_manager.broadcast_to_project(project_id, {
            "type": "asset_update",
            "event_type": event_type,
            "asset": {
                "id": asset_id,
                "name": asset_name,
                "user_id": user_id,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Log corresponding activity
        activity_types = {
            "created": ActivityType.ASSET_CREATED,
            "updated": ActivityType.ASSET_UPDATED,
            "deleted": ActivityType.ASSET_DELETED
        }
        
        if event_type in activity_types:
            await self.handle_activity_event(
                activity_type=activity_types[event_type],
                project_id=project_id,
                user_id=user_id,
                description=f"Asset '{asset_name}' {event_type}",
                metadata={"asset_id": asset_id, "asset_name": asset_name}
            )
    
    async def handle_collaboration_event(
        self,
        project_id: str,
        user_id: str,
        event_type: str,  # 'invited', 'joined', 'left', 'role_changed'
        target_user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle and broadcast collaboration events."""
        # Broadcast collaboration update
        await connection_manager.broadcast_to_project(project_id, {
            "type": "collaboration_update",
            "event_type": event_type,
            "user_id": user_id,
            "target_user_id": target_user_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Create notifications for relevant users
        if event_type == "invited" and target_user_id:
            await self.notification_service.create_notification(
                user_id=target_user_id,
                notification_type=NotificationType.INVITATION_RECEIVED,
                title="Project Invitation",
                message=f"You've been invited to collaborate on a project",
                entity_type="project",
                entity_id=project_id,
                metadata={"inviter_user_id": user_id}
            )
    
    async def handle_ai_job_event(
        self,
        project_id: str,
        job_id: str,
        user_id: str,
        event_type: str,  # 'started', 'completed', 'failed'
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle and broadcast AI job events."""
        # Broadcast AI job update
        await connection_manager.broadcast_to_project(project_id, {
            "type": "ai_job_update",
            "event_type": event_type,
            "job": {
                "id": job_id,
                "user_id": user_id,
                "model": model,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Send notification to job owner if completed or failed
        if event_type in ["completed", "failed"]:
            notification_type = (
                NotificationType.AI_JOB_COMPLETED if event_type == "completed"
                else NotificationType.AI_JOB_FAILED
            )
            
            await self.notification_service.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=f"AI Job {event_type.title()}",
                message=f"Your AI generation job has {event_type}",
                entity_type="ai_job",
                entity_id=job_id,
                metadata={"project_id": project_id, "model": model}
            )
        
        # Log corresponding activity
        activity_types = {
            "started": ActivityType.AI_GENERATION_STARTED,
            "completed": ActivityType.AI_GENERATION_COMPLETED,
            "failed": ActivityType.AI_GENERATION_FAILED
        }
        
        if event_type in activity_types:
            await self.handle_activity_event(
                activity_type=activity_types[event_type],
                project_id=project_id,
                user_id=user_id,
                description=f"AI generation job {event_type}",
                metadata={"job_id": job_id, "model": model}
            )


# Export components
__all__ = [
    'ConnectionManager',
    'RealTimeCollaborationService', 
    'connection_manager'
]
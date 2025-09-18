"""
Collaboration Service Layer for GameForge AI Platform
====================================================

Service layer handling all collaboration operations including:
- Project sharing and team management
- Activity logging and audit trails
- Invitation management
- Real-time collaboration events
"""
import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload, joinedload
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from gameforge.models.collaboration import (
    ProjectCollaboration, ProjectInvite, ActivityLog, Comment, 
    Notification, CollaborationRole, InviteStatus, ActivityType, NotificationType
)
from gameforge.models.projects import Project
from gameforge.core.logging_config import get_structured_logger, log_security_event

logger = get_structured_logger(__name__)


class CollaborationService:
    """Service for managing project collaboration."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # ========================================================================
    # Project Management
    # ========================================================================
    
    async def create_project(
        self,
        name: str,
        description: str,
        owner_id: str,
        visibility: str = "private",
        settings: Optional[Dict[str, Any]] = None
    ) -> Project:
        """Create a new project with the user as owner."""
        project = Project(
            name=name,
            description=description,
            owner_id=owner_id,
            visibility=visibility,
            settings=settings or {}
        )
        
        self.db.add(project)
        await self.db.flush()  # Get the project ID
        await self.db.refresh(project)  # Ensure attributes are available
        
        # Log project creation
        await self.log_activity(
            activity_type=ActivityType.PROJECT_CREATED,
            description=f"Project '{name}' created",
            project_id=project.id,
            user_id=owner_id,
            entity_type="project",
            entity_id=project.id
        )
        
        await self.db.commit()
        
        logger.info(
            "Project created",
            project_id=project.id,
            owner_id=owner_id,
            name=name
        )
        
        return project
    
    async def get_project(
        self,
        project_id: str,
        user_id: str,
        include_collaborations: bool = False
    ) -> Optional[Project]:
        """Get project if user has access."""
        query = select(Project).where(
            and_(
                Project.id == project_id,
                Project.deleted_at.is_(None)
            )
        )
        
        if include_collaborations:
            query = query.options(selectinload(Project.collaborations))
        
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            return None
            
        # Check access rights
        if not await self.can_user_access_project(project_id, user_id):
            return None
            
        return project
    
    async def get_user_projects(
        self,
        user_id: str,
        include_shared: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Get all projects accessible to a user."""
        # Start with owned projects
        owned_query = select(Project).where(
            and_(
                Project.owner_id == user_id,
                Project.deleted_at.is_(None)
            )
        )
        
        if include_shared:
            # Add shared projects through collaborations
            collaboration_subquery = select(ProjectCollaboration.project_id).where(
                and_(
                    ProjectCollaboration.user_id == user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
            
            shared_query = select(Project).where(
                and_(
                    Project.id.in_(collaboration_subquery),
                    Project.deleted_at.is_(None)
                )
            )
            
            # Union both queries
            query = owned_query.union(shared_query)
        else:
            query = owned_query
        
        query = query.order_by(desc(Project.last_activity_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ========================================================================
    # Collaboration Management
    # ========================================================================
    
    async def add_collaborator(
        self,
        project_id: str,
        user_id: str,
        collaborator_user_id: str,
        role: CollaborationRole,
        permissions: Optional[Dict[str, Any]] = None
    ) -> Optional[ProjectCollaboration]:
        """Add a collaborator to a project."""
        # Check if user can manage project
        if not await self.can_user_manage_project(project_id, user_id):
            return None
        
        # Check if collaboration already exists
        existing = await self.db.execute(
            select(ProjectCollaboration).where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == collaborator_user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
        )
        
        if existing.scalar_one_or_none():
            return None  # Already collaborating
        
        collaboration = ProjectCollaboration(
            project_id=project_id,
            user_id=collaborator_user_id,
            role=role,
            permissions=permissions or {},
            invited_by=user_id
        )
        
        self.db.add(collaboration)
        
        # Log the activity
        await self.log_activity(
            activity_type=ActivityType.MEMBER_JOINED,
            description=f"User added as {role.value}",
            project_id=project_id,
            user_id=user_id,
            entity_type="collaboration",
            entity_id=collaboration.id,
            metadata={"collaborator_user_id": collaborator_user_id, "role": role.value}
        )
        
        await self.db.commit()
        
        logger.info(
            "Collaborator added to project",
            project_id=project_id,
            collaborator_user_id=collaborator_user_id,
            role=role.value,
            invited_by=user_id
        )
        
        return collaboration
    
    async def update_collaborator_role(
        self,
        project_id: str,
        user_id: str,
        collaborator_user_id: str,
        new_role: CollaborationRole
    ) -> bool:
        """Update a collaborator's role."""
        if not await self.can_user_manage_project(project_id, user_id):
            return False
        
        result = await self.db.execute(
            update(ProjectCollaboration)
            .where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == collaborator_user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
            .values(role=new_role)
        )
        
        if result.rowcount > 0:
            await self.log_activity(
                activity_type=ActivityType.MEMBER_ROLE_CHANGED,
                description=f"User role changed to {new_role.value}",
                project_id=project_id,
                user_id=user_id,
                entity_type="collaboration",
                metadata={"collaborator_user_id": collaborator_user_id, "new_role": new_role.value}
            )
            
            await self.db.commit()
            return True
        
        return False
    
    async def remove_collaborator(
        self,
        project_id: str,
        user_id: str,
        collaborator_user_id: str
    ) -> bool:
        """Remove a collaborator from a project (soft delete)."""
        if not await self.can_user_manage_project(project_id, user_id):
            return False
        
        result = await self.db.execute(
            update(ProjectCollaboration)
            .where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == collaborator_user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
            .values(deleted_at=datetime.utcnow())
        )
        
        if result.rowcount > 0:
            await self.log_activity(
                activity_type=ActivityType.MEMBER_LEFT,
                description="User removed from project",
                project_id=project_id,
                user_id=user_id,
                entity_type="collaboration",
                metadata={"collaborator_user_id": collaborator_user_id}
            )
            
            await self.db.commit()
            return True
        
        return False
    
    async def get_project_collaborators(
        self,
        project_id: str,
        user_id: str
    ) -> List[ProjectCollaboration]:
        """Get all collaborators for a project."""
        if not await self.can_user_access_project(project_id, user_id):
            return []
        
        result = await self.db.execute(
            select(ProjectCollaboration)
            .where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
            .order_by(ProjectCollaboration.joined_at)
        )
        
        return result.scalars().all()
    
    # ========================================================================
    # Invitation System
    # ========================================================================
    
    async def create_invite(
        self,
        project_id: str,
        inviter_user_id: str,
        email: str,
        role: CollaborationRole,
        message: Optional[str] = None,
        expires_in_days: int = 7
    ) -> Optional[ProjectInvite]:
        """Create a project invitation."""
        if not await self.can_user_manage_project(project_id, inviter_user_id):
            return None
        
        # Check for existing pending invite
        existing = await self.db.execute(
            select(ProjectInvite).where(
                and_(
                    ProjectInvite.project_id == project_id,
                    ProjectInvite.email == email,
                    ProjectInvite.status == InviteStatus.PENDING
                )
            )
        )
        
        if existing.scalar_one_or_none():
            return None  # Pending invite already exists
        
        invite = ProjectInvite(
            project_id=project_id,
            email=email,
            role=role,
            message=message,
            invited_by=inviter_user_id,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        
        self.db.add(invite)
        await self.db.flush()
        
        # Log the invitation
        await self.log_activity(
            activity_type=ActivityType.MEMBER_INVITED,
            description=f"Invitation sent to {email}",
            project_id=project_id,
            user_id=inviter_user_id,
            entity_type="invite",
            entity_id=invite.id,
            metadata={"email": email, "role": role.value}
        )
        
        await self.db.commit()
        
        # Send invitation email (async)
        asyncio.create_task(self._send_invitation_email(invite))
        
        logger.info(
            "Project invitation created",
            project_id=project_id,
            email=email,
            role=role.value,
            invited_by=inviter_user_id
        )
        
        return invite
    
    async def accept_invite(
        self,
        token: str,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Accept a project invitation."""
        invite = await self.db.execute(
            select(ProjectInvite)
            .where(ProjectInvite.token == token)
            .options(selectinload(ProjectInvite.project))
        )
        invite = invite.scalar_one_or_none()
        
        if not invite:
            return False, "Invalid invitation token"
        
        if not invite.can_be_accepted():
            return False, "Invitation has expired or is no longer valid"
        
        # Create collaboration
        collaboration = ProjectCollaboration(
            project_id=invite.project_id,
            user_id=user_id,
            role=invite.role,
            invited_by=invite.invited_by
        )
        
        self.db.add(collaboration)
        
        # Update invite status
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_by = user_id
        invite.responded_at = datetime.utcnow()
        
        # Log the acceptance
        await self.log_activity(
            activity_type=ActivityType.MEMBER_JOINED,
            description=f"Invitation accepted by {user_id}",
            project_id=invite.project_id,
            user_id=user_id,
            entity_type="invite",
            entity_id=invite.id
        )
        
        await self.db.commit()
        
        return True, None
    
    async def get_pending_invites(
        self,
        email: str
    ) -> List[ProjectInvite]:
        """Get pending invitations for an email address."""
        result = await self.db.execute(
            select(ProjectInvite)
            .where(
                and_(
                    ProjectInvite.email == email,
                    ProjectInvite.status == InviteStatus.PENDING,
                    ProjectInvite.expires_at > datetime.utcnow()
                )
            )
            .options(selectinload(ProjectInvite.project))
            .order_by(desc(ProjectInvite.created_at))
        )
        
        return result.scalars().all()
    
    # ========================================================================
    # Activity Logging
    # ========================================================================
    
    async def log_activity(
        self,
        activity_type: ActivityType,
        description: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ActivityLog:
        """Log an activity."""
        activity = ActivityLog.log_activity(
            activity_type=activity_type,
            description=description,
            project_id=project_id,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(activity)
        
        # Update project's last activity time if applicable
        if project_id:
            await self.db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(last_activity_at=datetime.utcnow())
            )
        
        return activity
    
    async def get_project_activity(
        self,
        project_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activity feed for a project."""
        if not await self.can_user_access_project(project_id, user_id):
            return []
        
        result = await self.db.execute(
            select(ActivityLog)
            .where(ActivityLog.project_id == project_id)
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        return result.scalars().all()
    
    # ========================================================================
    # Permission Checking
    # ========================================================================
    
    async def can_user_access_project(
        self,
        project_id: str,
        user_id: str
    ) -> bool:
        """Check if user can access a project."""
        # Check if user is owner
        project = await self.db.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.deleted_at.is_(None)
                )
            )
        )
        project = project.scalar_one_or_none()
        
        if not project:
            return False
            
        if project.owner_id == user_id:
            return True
        
        # Check if user is a collaborator
        collaboration = await self.db.execute(
            select(ProjectCollaboration).where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
        )
        
        return collaboration.scalar_one_or_none() is not None
    
    async def can_user_manage_project(
        self,
        project_id: str,
        user_id: str
    ) -> bool:
        """Check if user can manage a project (add/remove collaborators)."""
        # Check if user is owner
        project = await self.db.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.deleted_at.is_(None)
                )
            )
        )
        project = project.scalar_one_or_none()
        
        if not project:
            return False
            
        if project.owner_id == user_id:
            return True
        
        # Check if user is admin collaborator
        collaboration = await self.db.execute(
            select(ProjectCollaboration).where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == user_id,
                    ProjectCollaboration.role.in_([
                        CollaborationRole.ADMIN,
                        CollaborationRole.OWNER
                    ]),
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
        )
        
        return collaboration.scalar_one_or_none() is not None
    
    async def get_user_role_in_project(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[CollaborationRole]:
        """Get user's role in a project."""
        # Check if user is owner
        project = await self.db.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == user_id,
                    Project.deleted_at.is_(None)
                )
            )
        )
        
        if project.scalar_one_or_none():
            return CollaborationRole.OWNER
        
        # Check collaboration
        collaboration = await self.db.execute(
            select(ProjectCollaboration).where(
                and_(
                    ProjectCollaboration.project_id == project_id,
                    ProjectCollaboration.user_id == user_id,
                    ProjectCollaboration.deleted_at.is_(None)
                )
            )
        )
        collaboration = collaboration.scalar_one_or_none()
        
        return collaboration.role if collaboration else None
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _send_invitation_email(self, invite: ProjectInvite) -> None:
        """Send invitation email (placeholder - implement with your email service)."""
        try:
            # This is a placeholder - implement with your email service
            # (SendGrid, AWS SES, etc.)
            logger.info(
                "Invitation email sent",
                invite_id=invite.id,
                email=invite.email,
                project_id=invite.project_id
            )
        except Exception as e:
            logger.error(
                "Failed to send invitation email",
                invite_id=invite.id,
                email=invite.email,
                error=str(e)
            )


class CommentService:
    """Service for managing comments on projects and assets."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.collaboration_service = CollaborationService(db_session)
    
    async def create_comment(
        self,
        project_id: str,
        user_id: str,
        content: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Optional[Comment]:
        """Create a new comment."""
        # Check if user can access the project
        if not await self.collaboration_service.can_user_access_project(project_id, user_id):
            return None
        
        # Handle threading
        thread_root_id = None
        if parent_id:
            parent = await self.db.execute(
                select(Comment).where(Comment.id == parent_id)
            )
            parent = parent.scalar_one_or_none()
            if parent:
                thread_root_id = parent.thread_root_id or parent.id
        
        comment = Comment(
            project_id=project_id,
            user_id=user_id,
            content=content,
            entity_type=entity_type,
            entity_id=entity_id,
            parent_id=parent_id,
            thread_root_id=thread_root_id
        )
        
        self.db.add(comment)
        await self.db.flush()
        
        # Update reply count for parent
        if parent_id:
            await self.db.execute(
                update(Comment)
                .where(Comment.id == parent_id)
                .values(reply_count=Comment.reply_count + 1)
            )
        
        # Log the activity
        await self.collaboration_service.log_activity(
            activity_type=ActivityType.COMMENT_CREATED,
            description="Comment added",
            project_id=project_id,
            user_id=user_id,
            entity_type="comment",
            entity_id=comment.id,
            metadata={
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "target_entity_type": entity_type,
                "target_entity_id": entity_id
            }
        )
        
        await self.db.commit()
        
        return comment
    
    async def get_comments(
        self,
        project_id: str,
        user_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Comment]:
        """Get comments for a project or specific entity."""
        if not await self.collaboration_service.can_user_access_project(project_id, user_id):
            return []
        
        query = select(Comment).where(
            and_(
                Comment.project_id == project_id,
                Comment.deleted_at.is_(None)
            )
        )
        
        if entity_type and entity_id:
            query = query.where(
                and_(
                    Comment.entity_type == entity_type,
                    Comment.entity_id == entity_id
                )
            )
        
        query = query.order_by(desc(Comment.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()


class NotificationService:
    """Service for managing user notifications."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata or {}
        )
        
        self.db.add(notification)
        await self.db.commit()
        
        return notification
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get user notifications."""
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.archived_at.is_(None)
            )
        )
        
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        
        query = query.order_by(desc(Notification.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None)
                )
            )
            .values(read_at=datetime.utcnow())
        )
        
        if result.rowcount > 0:
            await self.db.commit()
            return True
        
        return False


# Export services
__all__ = [
    'CollaborationService',
    'CommentService', 
    'NotificationService'
]
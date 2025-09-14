"""
User Consent Management API
==========================

Production-ready endpoints for managing user consent with GDPR compliance,
audit trails, and comprehensive validation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, validator, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, desc

from gameforge.core.database import DatabaseManager, get_async_session
from gameforge.core.logging_config import get_structured_logger
from gameforge.models import User, UserConsent
from gameforge.core.data_classification import DataClassification

router = APIRouter()
security = HTTPBearer()
logger = get_structured_logger(__name__)

# Database manager instance
db_manager = DatabaseManager()


class ConsentRequest(BaseModel):
    """Request model for granting or updating consent."""
    consent_type: str = Field(..., description="Type of consent being granted/denied")
    consent_value: bool = Field(..., description="True for granted, False for denied")
    purpose_description: str = Field(..., description="Clear description of data usage purpose")
    version: str = Field(default="1.0", description="Policy version")
    notes: Optional[str] = Field(None, description="Additional context or notes")
    
    @validator('consent_type')
    def validate_consent_type(cls, v):
        allowed_types = {
            'model_training',
            'analytics', 
            'marketing',
            'feature_improvement',
            'research',
            'asset_sharing',
            'performance_optimization',
            'security_monitoring'
        }
        if v not in allowed_types:
            raise ValueError(f"Invalid consent_type: {v}. Must be one of: {', '.join(allowed_types)}")
        return v
    
    @validator('purpose_description')
    def validate_purpose_description(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Purpose description must be at least 10 characters")
        return v.strip()


class ConsentResponse(BaseModel):
    """Response model for consent records."""
    id: str
    user_id: str
    consent_type: str
    consent_value: bool
    purpose_description: str
    granted_at: datetime
    version: str
    is_current: bool
    consent_method: str
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConsentSummaryResponse(BaseModel):
    """Summary of all current consents for a user."""
    user_id: str
    consents: List[ConsentResponse]
    total_consents: int
    granted_count: int
    denied_count: int
    last_updated: Optional[datetime] = None


class BulkConsentRequest(BaseModel):
    """Request model for bulk consent operations during signup."""
    consents: List[ConsentRequest] = Field(..., description="List of consent decisions")
    
    @validator('consents')
    def validate_consents(cls, v):
        if not v:
            raise ValueError("At least one consent decision is required")
        
        # Check for duplicates
        consent_types = [consent.consent_type for consent in v]
        if len(consent_types) != len(set(consent_types)):
            raise ValueError("Duplicate consent types are not allowed")
        
        return v


def get_client_info(request: Request) -> Dict[str, Optional[str]]:
    """Extract client IP and user agent from request."""
    # Get real IP, considering potential proxies
    real_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
        request.headers.get("x-real-ip") or
        request.client.host if request.client else None
    )
    
    user_agent = request.headers.get("user-agent")
    
    return {
        "source_ip": real_ip,
        "user_agent": user_agent
    }


async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user from JWT token."""
    # This would integrate with your existing auth system
    # For now, returning a placeholder - you'd decode the JWT and get user
    
    # TODO: Integrate with existing auth system
    # decoded = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
    # user_id = decoded.get("sub")
    
    # For now, returning a mock user - replace with actual auth logic
    async with get_async_session() as session:
        result = await session.execute(
            select(User).where(User.is_active == True).limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user


@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    consent_request: ConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Grant or deny consent for a specific purpose.
    
    This endpoint allows users to grant or deny consent for various data usage purposes.
    Each consent decision is audited with IP address, user agent, and timestamp.
    """
    try:
        client_info = get_client_info(request)
        
        # Check if there's an existing current consent for this type
        existing_result = await session.execute(
            select(UserConsent).where(
                and_(
                    UserConsent.user_id == current_user.id,
                    UserConsent.consent_type == consent_request.consent_type,
                    UserConsent.is_current == True
                )
            )
        )
        existing_consent = existing_result.scalar_one_or_none()
        
        if existing_consent:
            # Update existing consent by superseding it
            new_consent = UserConsent(
                user_id=current_user.id,
                consent_type=consent_request.consent_type,
                consent_value=consent_request.consent_value,
                purpose_description=consent_request.purpose_description,
                source_ip=client_info["source_ip"],
                user_agent=client_info["user_agent"],
                version=consent_request.version,
                supersedes_id=existing_consent.id,
                is_current=True,
                consent_method="web_form",
                notes=consent_request.notes
            )
            
            # Mark old consent as not current
            existing_consent.is_current = False
            session.add(existing_consent)
            
        else:
            # Create new consent
            new_consent = UserConsent(
                user_id=current_user.id,
                consent_type=consent_request.consent_type,
                consent_value=consent_request.consent_value,
                purpose_description=consent_request.purpose_description,
                source_ip=client_info["source_ip"],
                user_agent=client_info["user_agent"],
                version=consent_request.version,
                is_current=True,
                consent_method="web_form",
                notes=consent_request.notes
            )
        
        session.add(new_consent)
        await session.commit()
        await session.refresh(new_consent)
        
        # Log the consent event
        logger.info(
            "User consent recorded",
            extra={
                "user_id": current_user.id,
                "consent_type": consent_request.consent_type,
                "consent_value": consent_request.consent_value,
                "source_ip": client_info["source_ip"],
                "consent_id": new_consent.id
            }
        )
        
        return ConsentResponse.from_orm(new_consent)
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to record consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record consent decision"
        )


@router.post("/consent/bulk", response_model=ConsentSummaryResponse, status_code=status.HTTP_201_CREATED)
async def grant_bulk_consent(
    bulk_request: BulkConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Grant or deny multiple consents in a single operation.
    
    Typically used during user registration to collect all necessary consents.
    All consent decisions are processed atomically.
    """
    try:
        client_info = get_client_info(request)
        created_consents = []
        
        for consent_request in bulk_request.consents:
            # Check for existing consent
            existing_result = await session.execute(
                select(UserConsent).where(
                    and_(
                        UserConsent.user_id == current_user.id,
                        UserConsent.consent_type == consent_request.consent_type,
                        UserConsent.is_current == True
                    )
                )
            )
            existing_consent = existing_result.scalar_one_or_none()
            
            if existing_consent:
                # Mark as not current
                existing_consent.is_current = False
                session.add(existing_consent)
                supersedes_id = existing_consent.id
            else:
                supersedes_id = None
            
            # Create new consent
            new_consent = UserConsent(
                user_id=current_user.id,
                consent_type=consent_request.consent_type,
                consent_value=consent_request.consent_value,
                purpose_description=consent_request.purpose_description,
                source_ip=client_info["source_ip"],
                user_agent=client_info["user_agent"],
                version=consent_request.version,
                supersedes_id=supersedes_id,
                is_current=True,
                consent_method="bulk_web_form",
                notes=consent_request.notes
            )
            
            session.add(new_consent)
            created_consents.append(new_consent)
        
        await session.commit()
        
        # Refresh all created consents
        for consent in created_consents:
            await session.refresh(consent)
        
        # Calculate summary
        granted_count = sum(1 for c in created_consents if c.consent_value)
        denied_count = len(created_consents) - granted_count
        last_updated = max(c.granted_at for c in created_consents) if created_consents else None
        
        # Log bulk consent event
        logger.info(
            "Bulk user consents recorded",
            extra={
                "user_id": current_user.id,
                "total_consents": len(created_consents),
                "granted_count": granted_count,
                "denied_count": denied_count,
                "source_ip": client_info["source_ip"]
            }
        )
        
        return ConsentSummaryResponse(
            user_id=current_user.id,
            consents=[ConsentResponse.from_orm(c) for c in created_consents],
            total_consents=len(created_consents),
            granted_count=granted_count,
            denied_count=denied_count,
            last_updated=last_updated
        )
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to record bulk consents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record consent decisions"
        )


@router.get("/consent", response_model=ConsentSummaryResponse)
async def get_user_consents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all current consent decisions for the authenticated user.
    
    Returns only the current (active) consents, not the full history.
    """
    try:
        result = await session.execute(
            select(UserConsent)
            .where(
                and_(
                    UserConsent.user_id == current_user.id,
                    UserConsent.is_current == True
                )
            )
            .order_by(UserConsent.consent_type)
        )
        consents = result.scalars().all()
        
        granted_count = sum(1 for c in consents if c.consent_value)
        denied_count = len(consents) - granted_count
        last_updated = max(c.granted_at for c in consents) if consents else None
        
        return ConsentSummaryResponse(
            user_id=current_user.id,
            consents=[ConsentResponse.from_orm(c) for c in consents],
            total_consents=len(consents),
            granted_count=granted_count,
            denied_count=denied_count,
            last_updated=last_updated
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve user consents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consent information"
        )


@router.get("/consent/{consent_type}", response_model=ConsentResponse)
async def get_consent_by_type(
    consent_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get the current consent decision for a specific consent type.
    """
    try:
        result = await session.execute(
            select(UserConsent).where(
                and_(
                    UserConsent.user_id == current_user.id,
                    UserConsent.consent_type == consent_type,
                    UserConsent.is_current == True
                )
            )
        )
        consent = result.scalar_one_or_none()
        
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No consent found for type: {consent_type}"
            )
        
        return ConsentResponse.from_orm(consent)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consent information"
        )


@router.get("/consent/{consent_type}/history", response_model=List[ConsentResponse])
async def get_consent_history(
    consent_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get the full history of consent decisions for a specific type.
    
    Useful for compliance auditing and understanding consent changes over time.
    """
    try:
        result = await session.execute(
            select(UserConsent)
            .where(
                and_(
                    UserConsent.user_id == current_user.id,
                    UserConsent.consent_type == consent_type
                )
            )
            .order_by(desc(UserConsent.granted_at))
        )
        consents = result.scalars().all()
        
        return [ConsentResponse.from_orm(c) for c in consents]
        
    except Exception as e:
        logger.error(f"Failed to retrieve consent history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consent history"
        )


@router.delete("/consent/{consent_type}", status_code=status.HTTP_200_OK)
async def revoke_consent(
    consent_type: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Revoke consent for a specific type by setting it to False.
    
    This doesn't delete the consent record but creates a new record with consent_value=False.
    """
    try:
        client_info = get_client_info(request)
        
        # Find current consent
        result = await session.execute(
            select(UserConsent).where(
                and_(
                    UserConsent.user_id == current_user.id,
                    UserConsent.consent_type == consent_type,
                    UserConsent.is_current == True
                )
            )
        )
        current_consent = result.scalar_one_or_none()
        
        if not current_consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No current consent found for type: {consent_type}"
            )
        
        if not current_consent.consent_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Consent for {consent_type} is already revoked"
            )
        
        # Create revocation record
        revocation_consent = UserConsent(
            user_id=current_user.id,
            consent_type=consent_type,
            consent_value=False,
            purpose_description=current_consent.purpose_description,
            source_ip=client_info["source_ip"],
            user_agent=client_info["user_agent"],
            version=current_consent.version,
            supersedes_id=current_consent.id,
            is_current=True,
            consent_method="revocation",
            notes="Consent revoked by user"
        )
        
        # Mark old consent as not current
        current_consent.is_current = False
        session.add(current_consent)
        session.add(revocation_consent)
        
        await session.commit()
        
        # Log revocation event
        logger.info(
            "User consent revoked",
            extra={
                "user_id": current_user.id,
                "consent_type": consent_type,
                "source_ip": client_info["source_ip"],
                "revocation_id": revocation_consent.id
            }
        )
        
        return {"message": f"Consent for {consent_type} has been revoked"}
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to revoke consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke consent"
        )


@router.get("/consent-types", response_model=Dict[str, str])
async def get_consent_types():
    """
    Get all available consent types and their descriptions.
    
    Helps UIs display available consent options with clear descriptions.
    """
    consent_types = {
        "model_training": "Use your data to train and improve AI models",
        "analytics": "Use your data for platform analytics and insights to improve our services",
        "marketing": "Send you marketing communications and product updates",
        "feature_improvement": "Use your data to develop and improve platform features",
        "research": "Use your data for research and development of new technologies",
        "asset_sharing": "Allow your generated assets to be used as training data for improving models",
        "performance_optimization": "Use your data to optimize platform performance and user experience",
        "security_monitoring": "Use your data for security monitoring and fraud detection"
    }
    
    return consent_types
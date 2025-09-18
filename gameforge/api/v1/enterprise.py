"""
Enterprise API Routes for 44-Table Production Schema
===================================================

Provides API endpoints for billing, marketplace, organizations, and other
enterprise features in the GameForge AI Platform.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from gameforge.core.database import get_async_session
from gameforge.core.logging_config import get_structured_logger
from gameforge.models.enterprise import (
    # Billing & Subscription
    SubscriptionPlan, UserSubscription, BillingTransaction, PaymentMethod,
    # Marketplace & Community
    MarketplaceCategory, MarketplaceItem, MarketplaceReview, MarketplacePurchase,
    # Organization & Team Management
    Organization, OrganizationMember, OrganizationInvite,
    # Enhanced AI/ML Features
    ModelVersion, TrainingJob, AIModelMarketplace,
    # Advanced Security & Compliance
    SecurityScan, ComplianceReport,
    # Analytics & Reporting
    AnalyticsEvent, PerformanceMetric
)

router = APIRouter()
security = HTTPBearer()
logger = get_structured_logger(__name__)

# ============================================================================
# SUBSCRIPTION PLAN ENDPOINTS
# ============================================================================

class SubscriptionPlanResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: float
    price_yearly: float
    max_projects: int
    max_ai_requests_per_month: int
    max_storage_gb: int
    max_team_members: int
    features: dict
    is_active: bool

@router.get("/subscription-plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    session: AsyncSession = Depends(get_async_session)
):
    """Get all available subscription plans."""
    try:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        result = await session.execute(stmt)
        plans = result.scalars().all()
        
        return [
            SubscriptionPlanResponse(
                id=str(plan.id),
                name=plan.name,
                display_name=plan.display_name,
                description=plan.description,
                price_monthly=float(plan.price_monthly),
                price_yearly=float(plan.price_yearly),
                max_projects=plan.max_projects,
                max_ai_requests_per_month=plan.max_ai_requests_per_month,
                max_storage_gb=plan.max_storage_gb,
                max_team_members=plan.max_team_members,
                features=plan.features or {},
                is_active=plan.is_active
            ) for plan in plans
        ]
    except Exception as e:
        logger.error(f"Error fetching subscription plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")

# ============================================================================
# MARKETPLACE ENDPOINTS
# ============================================================================

class MarketplaceCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    parent_id: Optional[str]
    icon: Optional[str]
    color: Optional[str]

@router.get("/marketplace/categories", response_model=List[MarketplaceCategoryResponse])
async def get_marketplace_categories(
    session: AsyncSession = Depends(get_async_session)
):
    """Get all marketplace categories."""
    try:
        stmt = select(MarketplaceCategory).where(MarketplaceCategory.is_active == True)
        result = await session.execute(stmt)
        categories = result.scalars().all()
        
        return [
            MarketplaceCategoryResponse(
                id=str(category.id),
                name=category.name,
                slug=category.slug,
                description=category.description,
                parent_id=str(category.parent_id) if category.parent_id else None,
                icon=category.icon,
                color=category.color
            ) for category in categories
        ]
    except Exception as e:
        logger.error(f"Error fetching marketplace categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch marketplace categories")

class MarketplaceItemResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    price: float
    currency: str
    item_type: str
    preview_urls: List[str]
    tags: List[str]
    status: str
    download_count: int
    rating_average: float
    rating_count: int
    seller_id: str
    category_id: str

@router.get("/marketplace/items", response_model=List[MarketplaceItemResponse])
async def get_marketplace_items(
    category_id: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session)
):
    """Get marketplace items with filtering and pagination."""
    try:
        stmt = select(MarketplaceItem).where(MarketplaceItem.status == 'approved')
        
        if category_id:
            stmt = stmt.where(MarketplaceItem.category_id == uuid.UUID(category_id))
        
        if item_type:
            stmt = stmt.where(MarketplaceItem.item_type == item_type)
        
        if search:
            stmt = stmt.where(
                or_(
                    MarketplaceItem.title.ilike(f"%{search}%"),
                    MarketplaceItem.description.ilike(f"%{search}%")
                )
            )
        
        # Apply pagination
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)
        
        result = await session.execute(stmt)
        items = result.scalars().all()
        
        return [
            MarketplaceItemResponse(
                id=str(item.id),
                title=item.title,
                slug=item.slug,
                description=item.description,
                price=float(item.price),
                currency=item.currency,
                item_type=item.item_type,
                preview_urls=item.preview_urls or [],
                tags=item.tags or [],
                status=item.status,
                download_count=item.download_count,
                rating_average=float(item.rating_average),
                rating_count=item.rating_count,
                seller_id=str(item.seller_id),
                category_id=str(item.category_id)
            ) for item in items
        ]
    except Exception as e:
        logger.error(f"Error fetching marketplace items: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch marketplace items")

# ============================================================================
# ORGANIZATION ENDPOINTS
# ============================================================================

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_id: str
    max_members: int
    is_active: bool
    created_at: datetime

@router.get("/organizations", response_model=List[OrganizationResponse])
async def get_user_organizations(
    user_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get organizations for a user."""
    try:
        # Get organizations where user is a member
        stmt = (
            select(Organization)
            .join(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == uuid.UUID(user_id),
                    OrganizationMember.status == 'active',
                    Organization.is_active == True
                )
            )
        )
        
        result = await session.execute(stmt)
        organizations = result.scalars().all()
        
        return [
            OrganizationResponse(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                description=org.description,
                owner_id=str(org.owner_id),
                max_members=org.max_members,
                is_active=org.is_active,
                created_at=org.created_at
            ) for org in organizations
        ]
    except Exception as e:
        logger.error(f"Error fetching user organizations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch organizations")

# ============================================================================
# AI/ML TRAINING JOB ENDPOINTS
# ============================================================================

class TrainingJobResponse(BaseModel):
    id: str
    job_name: str
    job_type: str
    status: str
    progress_percent: int
    current_epoch: int
    total_epochs: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    error_message: Optional[str]

@router.get("/training-jobs", response_model=List[TrainingJobResponse])
async def get_training_jobs(
    user_id: str,
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session)
):
    """Get training jobs for a user."""
    try:
        stmt = select(TrainingJob).where(TrainingJob.user_id == uuid.UUID(user_id))
        
        if status:
            stmt = stmt.where(TrainingJob.status == status)
        
        stmt = stmt.order_by(TrainingJob.created_at.desc())
        
        result = await session.execute(stmt)
        jobs = result.scalars().all()
        
        return [
            TrainingJobResponse(
                id=str(job.id),
                job_name=job.job_name,
                job_type=job.job_type,
                status=job.status,
                progress_percent=job.progress_percent,
                current_epoch=job.current_epoch,
                total_epochs=job.total_epochs,
                started_at=job.started_at,
                completed_at=job.completed_at,
                estimated_cost=float(job.estimated_cost) if job.estimated_cost else None,
                actual_cost=float(job.actual_cost) if job.actual_cost else None,
                error_message=job.error_message
            ) for job in jobs
        ]
    except Exception as e:
        logger.error(f"Error fetching training jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch training jobs")

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

class AnalyticsEventRequest(BaseModel):
    event_type: str
    event_category: Optional[str]
    event_name: str
    properties: Optional[dict] = Field(default_factory=dict)
    user_agent: Optional[str]
    referrer: Optional[str]
    platform: Optional[str]

@router.post("/analytics/events")
async def track_analytics_event(
    user_id: str,
    event_data: AnalyticsEventRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Track an analytics event."""
    try:
        analytics_event = AnalyticsEvent(
            user_id=uuid.UUID(user_id),
            event_type=event_data.event_type,
            event_category=event_data.event_category,
            event_name=event_data.event_name,
            properties=event_data.properties,
            user_agent=event_data.user_agent,
            referrer=event_data.referrer,
            platform=event_data.platform
        )
        
        session.add(analytics_event)
        await session.commit()
        
        logger.info(f"Analytics event tracked: {event_data.event_type}")
        return {"status": "success", "message": "Event tracked successfully"}
        
    except Exception as e:
        logger.error(f"Error tracking analytics event: {e}")
        raise HTTPException(status_code=500, detail="Failed to track event")

# ============================================================================
# HEALTH CHECK FOR ENTERPRISE FEATURES
# ============================================================================

@router.get("/health/enterprise")
async def enterprise_health_check(
    session: AsyncSession = Depends(get_async_session)
):
    """Health check for enterprise features."""
    try:
        # Check if enterprise tables are accessible
        checks = {
            "subscription_plans": False,
            "marketplace_categories": False,
            "organizations": False,
            "training_jobs": False,
            "analytics_events": False
        }
        
        # Test subscription plans table
        try:
            stmt = select(SubscriptionPlan).limit(1)
            await session.execute(stmt)
            checks["subscription_plans"] = True
        except Exception:
            pass
        
        # Test marketplace categories table
        try:
            stmt = select(MarketplaceCategory).limit(1)
            await session.execute(stmt)
            checks["marketplace_categories"] = True
        except Exception:
            pass
        
        # Test organizations table
        try:
            stmt = select(Organization).limit(1)
            await session.execute(stmt)
            checks["organizations"] = True
        except Exception:
            pass
        
        # Test training jobs table
        try:
            stmt = select(TrainingJob).limit(1)
            await session.execute(stmt)
            checks["training_jobs"] = True
        except Exception:
            pass
        
        # Test analytics events table
        try:
            stmt = select(AnalyticsEvent).limit(1)
            await session.execute(stmt)
            checks["analytics_events"] = True
        except Exception:
            pass
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "enterprise_features": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Enterprise health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
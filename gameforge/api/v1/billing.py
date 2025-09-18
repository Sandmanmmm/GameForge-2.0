"""
Billing and Subscription API Endpoints for GameForge AI Platform
===============================================================

RESTful API endpoints for billing management:
- Subscription plans and management
- Payment methods and transactions
- Billing history and invoices
- Integration with Stripe payment processor
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, validator

from gameforge.core.database import get_async_session
from gameforge.models.enterprise import (
    SubscriptionPlan, UserSubscription, BillingTransaction, PaymentMethod
)
from gameforge.core.logging_config import get_structured_logger

logger = get_structured_logger(__name__)

# Create router
billing_router = APIRouter(prefix="/billing", tags=["billing"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SubscriptionPlanResponse(BaseModel):
    """Response model for subscription plans."""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: Decimal
    price_yearly: Decimal
    max_projects: int
    max_ai_requests_per_month: int
    max_storage_gb: int
    max_team_members: int
    features: Dict[str, Any]
    is_active: bool
    
    class Config:
        from_attributes = True


class UserSubscriptionCreate(BaseModel):
    """Request model for creating subscriptions."""
    plan_id: str = Field(..., description="Subscription plan ID")
    billing_cycle: str = Field("monthly", description="Billing cycle")
    payment_method_id: str = Field(..., description="Payment method ID")
    
    @validator('billing_cycle')
    def validate_billing_cycle(cls, v):
        if v not in ['monthly', 'yearly']:
            raise ValueError('billing_cycle must be monthly or yearly')
        return v


class UserSubscriptionResponse(BaseModel):
    """Response model for user subscriptions."""
    id: str
    user_id: str
    plan_id: str
    status: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_at: datetime
    plan: SubscriptionPlanResponse
    
    class Config:
        from_attributes = True


class BillingTransactionResponse(BaseModel):
    """Response model for billing transactions."""
    id: str
    user_id: str
    subscription_id: Optional[str]
    type: str
    amount: Decimal
    currency: str
    status: str
    description: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaymentMethodCreate(BaseModel):
    """Request model for adding payment methods."""
    stripe_payment_method_id: str = Field(..., description="Stripe payment method ID")
    type: str = Field(..., description="Payment method type")
    is_default: bool = Field(False, description="Set as default payment method")
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['card', 'paypal', 'bank_account']:
            raise ValueError('type must be card, paypal, or bank_account')
        return v


class PaymentMethodResponse(BaseModel):
    """Response model for payment methods."""
    id: str
    user_id: str
    type: str
    display_info: Dict[str, Any]
    is_default: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BillingStatsResponse(BaseModel):
    """Response model for billing statistics."""
    total_revenue: Decimal
    monthly_revenue: Decimal
    active_subscriptions: int
    subscription_breakdown: Dict[str, int]
    transaction_count: int
    average_revenue_per_user: Decimal


class InvoiceResponse(BaseModel):
    """Response model for invoices."""
    id: str
    user_id: str
    subscription_id: Optional[str]
    amount: Decimal
    currency: str
    status: str
    description: str
    invoice_date: datetime
    due_date: datetime
    paid_at: Optional[datetime]
    download_url: Optional[str]


# ============================================================================
# Helper Functions
# ============================================================================

def get_current_user_id() -> str:
    """Get current user ID from authentication - placeholder implementation."""
    # TODO: Implement actual JWT token validation
    return "550e8400-e29b-41d4-a716-446655440000"  # Placeholder UUID


# ============================================================================
# Subscription Plan Endpoints
# ============================================================================

@billing_router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_subscription_plans(
    active_only: bool = Query(True, description="Show only active plans"),
    db: AsyncSession = Depends(get_async_session)
):
    """List all available subscription plans."""
    try:
        query = select(SubscriptionPlan)
        
        if active_only:
            query = query.where(SubscriptionPlan.is_active == True)
        
        query = query.order_by(SubscriptionPlan.price_monthly)
        
        result = await db.execute(query)
        plans = result.scalars().all()
        
        return [SubscriptionPlanResponse.from_orm(plan) for plan in plans]
        
    except Exception as e:
        logger.error(f"Error listing subscription plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list subscription plans: {str(e)}"
        )


@billing_router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: str = Path(..., description="Subscription plan ID"),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific subscription plan."""
    try:
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found"
            )
        
        return SubscriptionPlanResponse.from_orm(plan)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription plan {plan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription plan: {str(e)}"
        )


# ============================================================================
# User Subscription Endpoints
# ============================================================================

@billing_router.get("/subscription", response_model=Optional[UserSubscriptionResponse])
async def get_user_subscription(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get current user's subscription."""
    try:
        query = select(UserSubscription).options(
            selectinload(UserSubscription.plan)
        ).where(
            and_(
                UserSubscription.user_id == current_user_id,
                UserSubscription.status == 'active'
            )
        )
        
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return None
        
        return UserSubscriptionResponse.from_orm(subscription)
        
    except Exception as e:
        logger.error(f"Error getting user subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user subscription: {str(e)}"
        )


@billing_router.post("/subscription", response_model=UserSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: UserSubscriptionCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new subscription."""
    try:
        # Check if user already has an active subscription
        existing_query = select(UserSubscription).where(
            and_(
                UserSubscription.user_id == current_user_id,
                UserSubscription.status == 'active'
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription"
            )
        
        # Get subscription plan
        plan_result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == subscription_data.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan or not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or inactive subscription plan"
            )
        
        # Calculate billing period
        start_date = datetime.utcnow()
        if subscription_data.billing_cycle == 'yearly':
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)
        
        # Create subscription
        subscription = UserSubscription(
            user_id=current_user_id,
            plan_id=subscription_data.plan_id,
            billing_cycle=subscription_data.billing_cycle,
            current_period_start=start_date,
            current_period_end=end_date,
            next_billing_date=end_date,
            status='active'
        )
        
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        
        # Load the plan relationship
        await db.refresh(subscription, ['plan'])
        
        logger.info(f"Subscription created: {subscription.id} for user {current_user_id}")
        return UserSubscriptionResponse.from_orm(subscription)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@billing_router.put("/subscription/cancel")
async def cancel_subscription(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Cancel current user's subscription."""
    try:
        # Get active subscription
        result = await db.execute(
            select(UserSubscription).where(
                and_(
                    UserSubscription.user_id == current_user_id,
                    UserSubscription.status == 'active'
                )
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Cancel subscription
        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Subscription cancelled: {subscription.id} for user {current_user_id}")
        return {"message": "Subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


# ============================================================================
# Payment Method Endpoints
# ============================================================================

@billing_router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def list_payment_methods(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """List user's payment methods."""
    try:
        result = await db.execute(
            select(PaymentMethod).where(
                and_(
                    PaymentMethod.user_id == current_user_id,
                    PaymentMethod.is_active == True
                )
            ).order_by(desc(PaymentMethod.is_default), PaymentMethod.created_at)
        )
        payment_methods = result.scalars().all()
        
        return [PaymentMethodResponse.from_orm(pm) for pm in payment_methods]
        
    except Exception as e:
        logger.error(f"Error listing payment methods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list payment methods: {str(e)}"
        )


@billing_router.post("/payment-methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    payment_method_data: PaymentMethodCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Add a new payment method."""
    try:
        # If this is set as default, remove default from other methods
        if payment_method_data.is_default:
            await db.execute(
                select(PaymentMethod).where(
                    and_(
                        PaymentMethod.user_id == current_user_id,
                        PaymentMethod.is_default == True
                    )
                ).update({PaymentMethod.is_default: False})
            )
        
        # Create payment method
        payment_method = PaymentMethod(
            user_id=current_user_id,
            stripe_payment_method_id=payment_method_data.stripe_payment_method_id,
            type=payment_method_data.type,
            is_default=payment_method_data.is_default,
            display_info={}  # Would be populated from Stripe webhook
        )
        
        db.add(payment_method)
        await db.commit()
        await db.refresh(payment_method)
        
        logger.info(f"Payment method added: {payment_method.id} for user {current_user_id}")
        return PaymentMethodResponse.from_orm(payment_method)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding payment method: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add payment method: {str(e)}"
        )


@billing_router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str = Path(..., description="Payment method ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a payment method."""
    try:
        # Get payment method
        result = await db.execute(
            select(PaymentMethod).where(
                and_(
                    PaymentMethod.id == payment_method_id,
                    PaymentMethod.user_id == current_user_id
                )
            )
        )
        payment_method = result.scalar_one_or_none()
        
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        
        # Soft delete
        payment_method.is_active = False
        await db.commit()
        
        logger.info(f"Payment method deleted: {payment_method_id} for user {current_user_id}")
        return {"message": "Payment method deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting payment method {payment_method_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete payment method: {str(e)}"
        )


# ============================================================================
# Transaction and Billing History Endpoints
# ============================================================================

@billing_router.get("/transactions", response_model=List[BillingTransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0, description="Number of transactions to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """List user's billing transactions."""
    try:
        query = select(BillingTransaction).where(
            BillingTransaction.user_id == current_user_id
        )
        
        if transaction_type:
            query = query.where(BillingTransaction.type == transaction_type)
        
        if status_filter:
            query = query.where(BillingTransaction.status == status_filter)
        
        query = query.order_by(desc(BillingTransaction.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        return [BillingTransactionResponse.from_orm(tx) for tx in transactions]
        
    except Exception as e:
        logger.error(f"Error listing transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list transactions: {str(e)}"
        )


@billing_router.get("/transactions/{transaction_id}", response_model=BillingTransactionResponse)
async def get_transaction(
    transaction_id: str = Path(..., description="Transaction ID"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific transaction."""
    try:
        result = await db.execute(
            select(BillingTransaction).where(
                and_(
                    BillingTransaction.id == transaction_id,
                    BillingTransaction.user_id == current_user_id
                )
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        return BillingTransactionResponse.from_orm(transaction)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction {transaction_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction: {str(e)}"
        )


# ============================================================================
# Billing Statistics and Reports
# ============================================================================

@billing_router.get("/stats", response_model=BillingStatsResponse)
async def get_billing_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_session)
):
    """Get billing statistics for the current user."""
    try:
        # Total spent by user
        total_query = select(func.sum(BillingTransaction.amount)).where(
            and_(
                BillingTransaction.user_id == current_user_id,
                BillingTransaction.status == 'completed'
            )
        )
        total_result = await db.execute(total_query)
        total_spent = total_result.scalar() or Decimal('0')
        
        # Monthly spending (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        monthly_query = select(func.sum(BillingTransaction.amount)).where(
            and_(
                BillingTransaction.user_id == current_user_id,
                BillingTransaction.status == 'completed',
                BillingTransaction.created_at >= thirty_days_ago
            )
        )
        monthly_result = await db.execute(monthly_query)
        monthly_spent = monthly_result.scalar() or Decimal('0')
        
        # Transaction count
        count_query = select(func.count(BillingTransaction.id)).where(
            BillingTransaction.user_id == current_user_id
        )
        count_result = await db.execute(count_query)
        transaction_count = count_result.scalar() or 0
        
        # Active subscriptions (for this user, should be 0 or 1)
        active_subs_query = select(func.count(UserSubscription.id)).where(
            and_(
                UserSubscription.user_id == current_user_id,
                UserSubscription.status == 'active'
            )
        )
        active_subs_result = await db.execute(active_subs_query)
        active_subscriptions = active_subs_result.scalar() or 0
        
        return BillingStatsResponse(
            total_revenue=total_spent,
            monthly_revenue=monthly_spent,
            active_subscriptions=active_subscriptions,
            subscription_breakdown={},
            transaction_count=transaction_count,
            average_revenue_per_user=total_spent if transaction_count > 0 else Decimal('0')
        )
        
    except Exception as e:
        logger.error(f"Error getting billing stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing statistics: {str(e)}"
        )

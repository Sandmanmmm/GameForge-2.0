"""
API v1 router aggregation.
"""
from fastapi import APIRouter

from gameforge.api.v1 import (
    ai, assets, datasets, models, auth, ml_platform, 
    monitoring, consent, enterprise, projects, billing, notifications
)
from gameforge.api.collaboration import collaboration_router


api_router = APIRouter()

# Include all v1 routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    consent.router,
    prefix="/users",
    tags=["user-consent"]
)

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["ai-generation"]
)

api_router.include_router(
    assets.router,
    prefix="/assets",
    tags=["assets"]
)

api_router.include_router(
    datasets.router,
    prefix="/datasets",
    tags=["datasets"]
)

api_router.include_router(
    models.router,
    prefix="/models",
    tags=["models"]
)

api_router.include_router(
    ml_platform.router,
    prefix="/ml-platform",
    tags=["ml-platform"]
)

api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["monitoring"]
)

# Enterprise features for 44-table production schema
api_router.include_router(
    enterprise.router,
    prefix="/enterprise",
    tags=["enterprise"]
)

# Projects management
api_router.include_router(
    projects.projects_router,
    tags=["projects"]
)

# Billing and subscriptions
api_router.include_router(
    billing.billing_router,
    tags=["billing"]
)

# Notifications and real-time updates
api_router.include_router(
    notifications.notifications_router,
    tags=["notifications"]
)

# Collaboration features
api_router.include_router(
    collaboration_router,
    tags=["collaboration"]
)
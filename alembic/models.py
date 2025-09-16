"""
Migration-only models for Alembic.
This file contains only the Base and essential model definitions needed for migrations.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# Add models path for external models directory
sys.path.append(r"D:\models")

# Direct import without going through the problematic models package
from gameforge.models.base import Base, User, Project, Asset, APIKey, AuditLog, UsageMetrics

# Make sure all models are available for autogenerate
__all__ = ['Base', 'User', 'Project', 'Asset', 'APIKey', 'AuditLog', 'UsageMetrics']
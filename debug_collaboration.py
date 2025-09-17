#!/usr/bin/env python3
"""
Test script to debug collaboration model registration.
"""
from gameforge.core.base import Base

print("Importing collaboration models...")

# Import collaboration models directly
from gameforge.models.collaboration import (
    ProjectCollaboration, ProjectInvite, ActivityLog, Comment, Notification
)

print("\nTables in Base.metadata after importing collaboration models:")
for table_name in sorted(Base.metadata.tables.keys()):
    print(f"  - {table_name}")

print(f"\nTotal tables: {len(Base.metadata.tables)}")

# Test if specific tables exist
collaboration_tables = [
    'project_collaborations', 'project_invites', 'activity_logs', 
    'comments', 'notifications'
]

print(f"\nChecking for collaboration tables:")
for table in collaboration_tables:
    exists = table in Base.metadata.tables
    print(f"  - {table}: {'✅' if exists else '❌'}")
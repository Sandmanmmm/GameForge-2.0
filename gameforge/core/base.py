"""
SQLAlchemy Base Model Configuration
===================================

This module provides the declarative base for all GameForge database models.
It's kept separate from the database connection logic to avoid circular imports
and enable clean migrations.
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# Define naming convention for constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s", 
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=naming_convention)

# Create the declarative base
Base = declarative_base(metadata=metadata)

# Export the base
__all__ = ['Base']
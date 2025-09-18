"""add_remaining_projects_columns

Revision ID: 6fad1d675ea3
Revises: d95a4301ee91
Create Date: 2025-09-18 02:45:08.046319

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6fad1d675ea3'
down_revision = 'd95a4301ee91'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add remaining missing columns to projects table."""
    # Add missing boolean columns
    op.add_column('projects', sa.Column('is_template', sa.Boolean(), nullable=True, default=False))
    op.add_column('projects', sa.Column('ai_generated_content', sa.Boolean(), nullable=True, default=False))
    op.add_column('projects', sa.Column('automation_enabled', sa.Boolean(), nullable=True, default=False))
    
    # Add missing string columns
    op.add_column('projects', sa.Column('version', sa.String(length=20), nullable=True, default='1.0.0'))
    op.add_column('projects', sa.Column('license', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('download_url', sa.String(length=500), nullable=True))
    
    # Add missing integer columns
    op.add_column('projects', sa.Column('like_count', sa.Integer(), nullable=True, default=0))
    op.add_column('projects', sa.Column('storage_used_bytes', sa.Integer(), nullable=True, default=0))
    op.add_column('projects', sa.Column('storage_limit_bytes', sa.Integer(), nullable=True, default=5368709120))
    op.add_column('projects', sa.Column('asset_count', sa.Integer(), nullable=True, default=0))
    
    # Add missing datetime columns
    op.add_column('projects', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.add_column('projects', sa.Column('archived_at', sa.DateTime(), nullable=True))
    
    # Add search vector column (PostgreSQL specific)
    op.execute('ALTER TABLE projects ADD COLUMN search_vector tsvector')


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column('projects', 'search_vector')
    op.drop_column('projects', 'archived_at')
    op.drop_column('projects', 'published_at')
    op.drop_column('projects', 'asset_count')
    op.drop_column('projects', 'storage_limit_bytes')
    op.drop_column('projects', 'storage_used_bytes')
    op.drop_column('projects', 'like_count')
    op.drop_column('projects', 'download_url')
    op.drop_column('projects', 'license')
    op.drop_column('projects', 'version')
    op.drop_column('projects', 'automation_enabled')
    op.drop_column('projects', 'ai_generated_content')
    op.drop_column('projects', 'is_template')

"""add_missing_projects_summary_column

Revision ID: d95a4301ee91
Revises: 8d99f64145c1
Create Date: 2025-09-18 02:44:19.441348

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd95a4301ee91'
down_revision = '8d99f64145c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns that exist in models but not in database."""
    # Add projects.summary column
    op.add_column('projects', sa.Column('summary', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove the added columns."""
    # Remove projects.summary column
    op.drop_column('projects', 'summary')

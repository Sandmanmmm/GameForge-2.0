"""add_minimal_seed_data

Revision ID: 0c2431c1f98c
Revises: afee3109eb72
Create Date: 2025-09-17 15:14:12.211066

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import uuid
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '0c2431c1f98c'
down_revision = 'afee3109eb72'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add minimal essential seed data for production deployment."""
    
    # Get database connection
    conn = op.get_bind()
    
    # Create default ADMIN user
    admin_user_id = str(uuid.uuid4())
    
    conn.execute(text("""
        INSERT INTO users (
            id, username, email, password_hash, name, role,
            is_active, is_verified, created_at, updated_at
        ) VALUES (
            :user_id, 'admin', 'admin@gameforge.dev',
            '$2b$12$LQv3c1yqBwEHxDhBqK4HPuM5m3H8K9.P2yQ1eCf6ZpA5R8nG7tQ2S',
            'System Administrator', 'ADMIN',
            true, true, :now, :now
        )
    """), {
        'user_id': admin_user_id,
        'now': datetime.utcnow()
    })
    
    print("✅ Minimal seed data created successfully!")


def downgrade() -> None:
    """Remove minimal seed data."""
    
    # Get database connection
    conn = op.get_bind()
    
    # Remove admin user
    conn.execute(text("""
        DELETE FROM users WHERE username = 'admin' AND email = 'admin@gameforge.dev'
    """))
    
    print("✅ Minimal seed data removed successfully!")

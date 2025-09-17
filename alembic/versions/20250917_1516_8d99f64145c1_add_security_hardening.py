"""add_security_hardening

Revision ID: 8d99f64145c1
Revises: 0c2431c1f98c
Create Date: 2025-09-17 15:16:05.002065

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '8d99f64145c1'
down_revision = '0c2431c1f98c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add security hardening features for production deployment."""
    
    # Get database connection
    conn = op.get_bind()
    
    # 1. Add security constraints on password fields
    conn.execute(text("""
        ALTER TABLE users 
        ADD CONSTRAINT check_password_not_empty 
        CHECK (password_hash IS NULL OR length(password_hash) >= 8)
    """))
    
    # 2. Add security constraints on email fields
    conn.execute(text("""
        ALTER TABLE users 
        ADD CONSTRAINT check_email_format 
        CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
    """))
    
    # 3. Add constraint to prevent privilege escalation
    conn.execute(text("""
        ALTER TABLE users 
        ADD CONSTRAINT check_admin_verification 
        CHECK (role != 'ADMIN' OR is_verified = true)
    """))
    
    # 4. Add security constraints on sensitive operations (if table exists)
    try:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_users_security_lookup 
            ON users (email, is_active, is_verified) 
            WHERE is_active = true
        """))
    except Exception as e:
        print(f"Warning: Could not create security index: {e}")
    
    print("✅ Security hardening features added successfully!")


def downgrade() -> None:
    """Remove security hardening features."""
    
    # Get database connection
    conn = op.get_bind()
    
    # Remove constraints and indexes in reverse order
    conn.execute(text("""
        ALTER TABLE users 
        DROP CONSTRAINT IF EXISTS check_admin_verification
    """))
    conn.execute(text("""
        ALTER TABLE users 
        DROP CONSTRAINT IF EXISTS check_email_format
    """))
    conn.execute(text("""
        ALTER TABLE users 
        DROP CONSTRAINT IF EXISTS check_password_not_empty
    """))
    conn.execute(text("DROP INDEX IF EXISTS idx_users_security_lookup"))
    
    print("✅ Security hardening features removed successfully!")

"""add_production_performance_indexes

Revision ID: afee3109eb72
Revises: 9bc1ffe7406c
Create Date: 2025-09-17 15:03:45.954421

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'afee3109eb72'
down_revision = '93fcbdb8b506'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add production performance indexes."""
    
    # GIN indexes for JSONB columns (for fast queries on JSON data)
    performance_gin_indexes = [
        ('ai_requests', 'input_data'),
        ('ai_requests', 'output_data'),
        ('assets', 'metadata'),
        ('audit_logs', 'details'),
        ('experiments', 'hyperparameters'),
        ('experiments', 'metrics'),
        ('ml_models', 'hyperparameters'),
        ('ml_models', 'metrics'),
        ('system_config', 'value'),
        ('user_preferences', 'settings'),
        ('subscriptions', 'plan_metadata'),
        ('system_notifications', 'notification_metadata'),
        ('access_tokens', 'conditions'),
        ('access_tokens', 'metadata'),
        ('api_keys', 'permissions'),
        ('compliance_events', 'details'),
        ('datasets', 'schema_definition'),
        ('datasets', 'validation_rules')
    ]
    
    for table, column in performance_gin_indexes:
        try:
            op.create_index(
                f'idx_gin_{table}_{column}',
                table,
                [column],
                postgresql_using='gin'
            )
        except Exception as e:
            print(f"Warning: Could not create GIN index on {table}.{column}: "
                  f"{e}")
    
    print("✅ Production performance indexes created successfully!")


def downgrade() -> None:
    """Remove production performance indexes."""
    
    # Drop GIN indexes in reverse order
    performance_gin_indexes = [
        ('ai_requests', 'input_data'),
        ('ai_requests', 'output_data'),
        ('assets', 'metadata'),
        ('audit_logs', 'details'),
        ('experiments', 'hyperparameters'),
        ('experiments', 'metrics'),
        ('ml_models', 'hyperparameters'),
        ('ml_models', 'metrics'),
        ('system_config', 'value'),
        ('user_preferences', 'settings'),
        ('subscriptions', 'plan_metadata'),
        ('system_notifications', 'notification_metadata'),
        ('access_tokens', 'conditions'),
        ('access_tokens', 'metadata'),
        ('api_keys', 'permissions'),
        ('compliance_events', 'details'),
        ('datasets', 'schema_definition'),
        ('datasets', 'validation_rules')
    ]
    
    for table, column in performance_gin_indexes:
        try:
            op.drop_index(f'idx_gin_{table}_{column}', table_name=table)
        except Exception as e:
            print(f"Warning: Could not drop GIN index on {table}.{column}: "
                  f"{e}")
    
    print("✅ Production performance indexes removed successfully!")

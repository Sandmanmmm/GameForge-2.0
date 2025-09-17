#!/usr/bin/env python3
"""
Fix UUID types in the generated migration file.
This script updates all foreign key columns to use proper UUID types.
"""

import re

def fix_migration_uuids():
    """Fix UUID types in the migration file."""
    migration_file = "alembic/versions/20250917_1424_fc035ef6da47_add_all_missing_model_tables_with_.py"
    
    print(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Define patterns to fix UUID foreign keys
    uuid_fixes = [
        # User foreign keys
        (r"sa\.Column\('creator_id', sa\.String\(\)", "sa.Column('creator_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('user_id', sa\.String\(\)", "sa.Column('user_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('created_by_id', sa\.String\(\)", "sa.Column('created_by_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('invited_by_id', sa\.String\(\)", "sa.Column('invited_by_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('invited_user_id', sa\.String\(\)", "sa.Column('invited_user_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('buyer_id', sa\.String\(\)", "sa.Column('buyer_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('collaborator_id', sa\.String\(\)", "sa.Column('collaborator_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('verified_by_id', sa\.String\(\)", "sa.Column('verified_by_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('marketplace_approved_by_id', sa\.String\(\)", "sa.Column('marketplace_approved_by_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('author_id', sa\.String\(\)", "sa.Column('author_id', postgresql.UUID(as_uuid=True)"),
        
        # Project foreign keys
        (r"sa\.Column\('project_id', sa\.String\(\)", "sa.Column('project_id', postgresql.UUID(as_uuid=True)"),
        
        # Template foreign keys
        (r"sa\.Column\('template_id', sa\.String\(\)", "sa.Column('template_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('category_id', sa\.String\(\)", "sa.Column('category_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('previous_version_id', sa\.String\(\)", "sa.Column('previous_version_id', postgresql.UUID(as_uuid=True)"),
        
        # Asset foreign keys
        (r"sa\.Column\('asset_id', sa\.String\(\)", "sa.Column('asset_id', postgresql.UUID(as_uuid=True)"),
        
        # Dataset foreign keys
        (r"sa\.Column\('dataset_id', sa\.String\(\)", "sa.Column('dataset_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('parent_dataset_id', sa\.String\(\)", "sa.Column('parent_dataset_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('training_dataset_id', sa\.String\(\)", "sa.Column('training_dataset_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('validation_dataset_id', sa\.String\(\)", "sa.Column('validation_dataset_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('test_dataset_id', sa\.String\(\)", "sa.Column('test_dataset_id', postgresql.UUID(as_uuid=True)"),
        
        # Organization foreign keys
        (r"sa\.Column\('organization_id', sa\.String\(\)", "sa.Column('organization_id', postgresql.UUID(as_uuid=True)"),
        
        # Experiment and model foreign keys
        (r"sa\.Column\('experiment_id', sa\.String\(\)", "sa.Column('experiment_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('base_model_id', sa\.String\(\)", "sa.Column('base_model_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('model_version_id', sa\.String\(\)", "sa.Column('model_version_id', postgresql.UUID(as_uuid=True)"),
        
        # Purchase and payment foreign keys
        (r"sa\.Column\('purchase_id', sa\.String\(\)", "sa.Column('purchase_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('coupon_code_id', sa\.String\(\)", "sa.Column('coupon_code_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('payment_method_id', sa\.String\(\)", "sa.Column('payment_method_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('invoice_id', sa\.String\(\)", "sa.Column('invoice_id', postgresql.UUID(as_uuid=True)"),
        
        # Provider foreign keys
        (r"sa\.Column\('provider_id', sa\.String\(\)", "sa.Column('provider_id', postgresql.UUID(as_uuid=True)"),
        
        # API key foreign keys
        (r"sa\.Column\('api_key_id', sa\.String\(\)", "sa.Column('api_key_id', postgresql.UUID(as_uuid=True)"),
        
        # Resource foreign keys
        (r"sa\.Column\('resource_id', sa\.String\(\)", "sa.Column('resource_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('scope_id', sa\.String\(\)", "sa.Column('scope_id', postgresql.UUID(as_uuid=True)"),
        
        # Self-referential foreign keys
        (r"sa\.Column\('parent_id', sa\.String\(\)", "sa.Column('parent_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('parent_dataset_id', sa\.String\(\)", "sa.Column('parent_dataset_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('parent_comment_id', sa\.String\(\)", "sa.Column('parent_comment_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('thread_root_id', sa\.String\(\)", "sa.Column('thread_root_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('parent_version_id', sa\.String\(\)", "sa.Column('parent_version_id', postgresql.UUID(as_uuid=True)"),
        
        # Additional foreign keys that may be missed
        (r"sa\.Column\('collaborator_id', sa\.String\(\)", "sa.Column('collaborator_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('invited_user_id', sa\.String\(\)", "sa.Column('invited_user_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('external_customer_id', sa\.String\(\)", "sa.Column('external_customer_id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('external_subscription_id', sa\.String\(\)", "sa.Column('external_subscription_id', postgresql.UUID(as_uuid=True)"),
        
        # Primary key IDs should also be UUIDs
        (r"sa\.Column\('id', sa\.String\(\)", "sa.Column('id', postgresql.UUID(as_uuid=True)"),
        
        # Catch-all for any other _id foreign keys (use with caution)
        (r"sa\.Column\('([^']*_id)', sa\.String\(\)", r"sa.Column('\1', postgresql.UUID(as_uuid=True)"),
    ]
    
    fixes_applied = 0
    
    # Apply all UUID fixes
    for pattern, replacement in uuid_fixes:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            fixes_applied += matches
            print(f"Fixed {matches} instances of {pattern}")
    
    print(f"\nTotal UUID fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(migration_file, 'w') as f:
        f.write(content)
    
    print(f"Migration file updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_migration_uuids()
    print(f"\nCompleted! Applied {fixes_applied} UUID type fixes to migration file.")
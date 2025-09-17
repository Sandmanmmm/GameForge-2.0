#!/usr/bin/env python3
"""
Fix ALTER COLUMN operations that incorrectly convert UUID foreign keys back to String.
This script ensures that all foreign key columns maintain proper UUID types.
"""

import re

def fix_alter_column_operations():
    """Fix ALTER COLUMN operations to maintain UUID types for foreign keys."""
    migration_file = "alembic/versions/20250917_1424_fc035ef6da47_add_all_missing_model_tables_with_.py"
    
    print(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Pattern to match ALTER COLUMN operations that convert UUID to String for foreign keys
    # These operations should maintain UUID type instead
    uuid_alter_patterns = [
        # Primary key id columns
        (r"op\.alter_column\('(\w+)', 'id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.id as UUID primary key - no alteration needed"),
        
        # User foreign keys
        (r"op\.alter_column\('(\w+)', 'user_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.user_id as UUID foreign key - no alteration needed"),
        (r"op\.alter_column\('(\w+)', 'creator_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.creator_id as UUID foreign key - no alteration needed"),
        (r"op\.alter_column\('(\w+)', 'created_by_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.created_by_id as UUID foreign key - no alteration needed"),
        
        # Project foreign keys
        (r"op\.alter_column\('(\w+)', 'project_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.project_id as UUID foreign key - no alteration needed"),
        
        # Asset foreign keys
        (r"op\.alter_column\('(\w+)', 'asset_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.asset_id as UUID foreign key - no alteration needed"),
        
        # Dataset foreign keys
        (r"op\.alter_column\('(\w+)', 'dataset_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.dataset_id as UUID foreign key - no alteration needed"),
        (r"op\.alter_column\('(\w+)', 'parent_dataset_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.parent_dataset_id as UUID foreign key - no alteration needed"),
        
        # Organization foreign keys
        (r"op\.alter_column\('(\w+)', 'organization_id',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),", 
         r"# Keep \1.organization_id as UUID foreign key - no alteration needed"),
        
        # Generic _id pattern to catch any remaining UUID foreign keys
        (r"op\.alter_column\('(\w+)', '([^']*_id)',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),([^)]*\))", 
         r"# Keep \1.\2 as UUID foreign key - no alteration needed"),
    ]
    
    fixes_applied = 0
    
    # Apply all ALTER COLUMN fixes
    for pattern, replacement in uuid_alter_patterns:
        matches = len(re.findall(pattern, content, re.MULTILINE | re.DOTALL))
        if matches > 0:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
            fixes_applied += matches
            print(f"Fixed {matches} ALTER COLUMN operations for pattern: {pattern[:50]}...")
    
    print(f"\nTotal ALTER COLUMN fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(migration_file, 'w') as f:
        f.write(content)
    
    print(f"Migration file updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_alter_column_operations()
    print(f"\nCompleted! Applied {fixes_applied} ALTER COLUMN fixes to migration file.")
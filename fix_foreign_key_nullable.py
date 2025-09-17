#!/usr/bin/env python3
"""
Fix foreign key nullable issues in migration.
"""

import re
import glob

def fix_foreign_key_nullable():
    """Fix foreign key columns that should be nullable."""
    
    # Find the latest migration file
    migration_files = glob.glob("alembic/versions/*.py")
    latest_migration = max(migration_files, key=lambda x: x.split('_')[1] if '_' in x else '0')
    print(f"Found latest migration: {latest_migration}")
    
    with open(latest_migration, 'r') as f:
        content = f.read()
    
    fixes_applied = 0
    
    # Pattern to find ADD COLUMN operations for foreign keys that are NOT NULL
    fk_add_patterns = [
        # provider_id should be nullable for storage_configs
        (r"op\.add_column\('storage_configs', sa\.Column\('provider_id', postgresql\.UUID\(as_uuid=True\), nullable=False\)\)",
         "op.add_column('storage_configs', sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=True))"),
        
        # Other foreign keys that might cause issues
        (r"op\.add_column\('([^']+)', sa\.Column\('([^']*_id)', postgresql\.UUID\(as_uuid=True\), nullable=False\)\)",
         r"op.add_column('\1', sa.Column('\2', postgresql.UUID(as_uuid=True), nullable=True))"),
    ]
    
    print("Fixing foreign key nullable issues...")
    for pattern, replacement in fk_add_patterns:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            fixes_applied += matches
            print(f"  Fixed {matches} foreign key nullable issues")
    
    print(f"\nTotal fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(latest_migration, 'w') as f:
        f.write(content)
    
    print(f"Migration file {latest_migration} updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_foreign_key_nullable()
    print(f"\nCompleted! Applied {fixes_applied} fixes to migration file.")
#!/usr/bin/env python3
"""
Fix enum creation order in migration.
"""

import re
import glob

def fix_enum_creation_order():
    """Fix enum types that need to be created before use."""
    
    # Find the latest migration file
    migration_files = glob.glob("alembic/versions/*.py")
    latest_migration = max(migration_files, key=lambda x: x.split('_')[1] if '_' in x else '0')
    print(f"Found latest migration: {latest_migration}")
    
    with open(latest_migration, 'r') as f:
        content = f.read()
    
    fixes_applied = 0
    
    # Find all enum types that need to be created
    enum_patterns = [
        'storagestatus',
        'airequeststatus', 
        'dataclassification',
        'userrole',
        'authprovider'
    ]
    
    # Create enum definitions at the top of upgrade function
    enum_creates = []
    for enum_name in enum_patterns:
        if enum_name.lower() in content.lower():
            # Create the enum type first
            if enum_name == 'storagestatus':
                enum_creates.append(f"    sa.Enum('ACTIVE', 'INACTIVE', 'MAINTENANCE', 'ERROR', 'TESTING', name='{enum_name}').create(op.get_bind())")
            elif enum_name == 'airequeststatus':
                enum_creates.append(f"    sa.Enum('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', name='{enum_name}').create(op.get_bind())")
            elif enum_name == 'dataclassification':
                enum_creates.append(f"    sa.Enum('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', 'PERSONAL_DATA', 'SENSITIVE_PERSONAL_DATA', name='{enum_name}').create(op.get_bind())")
            elif enum_name == 'userrole':
                enum_creates.append(f"    sa.Enum('ADMIN', 'USER', 'MODERATOR', 'DEVELOPER', name='{enum_name}').create(op.get_bind())")
            elif enum_name == 'authprovider':
                enum_creates.append(f"    sa.Enum('LOCAL', 'GITHUB', 'GOOGLE', 'DISCORD', name='{enum_name}').create(op.get_bind())")
    
    if enum_creates:
        print(f"Creating {len(enum_creates)} enum types...")
        
        # Find the upgrade function start
        upgrade_start = re.search(r'def upgrade\(\):\s*\n', content)
        if upgrade_start:
            # Insert enum creations after the upgrade function declaration
            insert_pos = upgrade_start.end()
            enum_creation_block = "\n    # Create enum types first\n" + "\n".join(enum_creates) + "\n\n"
            content = content[:insert_pos] + enum_creation_block + content[insert_pos:]
            fixes_applied += len(enum_creates)
    
    print(f"\nTotal fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(latest_migration, 'w') as f:
        f.write(content)
    
    print(f"Migration file {latest_migration} updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_enum_creation_order()
    print(f"\nCompleted! Applied {fixes_applied} fixes to migration file.")
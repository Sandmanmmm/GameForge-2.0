#!/usr/bin/env python3
"""
Fix corrupted migration file by removing leftover fragments from alter column operations.
"""

import re

def fix_migration_corruption():
    migration_file = 'alembic/versions/20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'
    
    print("Reading migration file...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Fixing corrupted fragments...")
    
    # Find and remove orphaned fragments - patterns that are incomplete alter column remnants
    patterns_to_remove = [
        # Orphaned commas and incomplete lines
        r',\s*\n\s+type_=.*?\n',
        r',\s*\n\s+existing_nullable=.*?\n',
        r',\s*\n\s+existing_server_default=.*?\n',
        r',\s*\n\s+nullable=.*?\)\n',
        r',\s*\n\s+nullable=.*?\n',
        # Standalone orphaned commas
        r'^,\s*$',
        # Incomplete parameter fragments
        r'\s+type_=.*?(?=\n\s+[a-z_]+=|\n    op\.|\n\n|\Z)',
        r'\s+existing_nullable=.*?(?=\n\s+[a-z_]+=|\n    op\.|\n\n|\Z)',
        r'\s+existing_server_default=.*?(?=\n\s+[a-z_]+=|\n    op\.|\n\n|\Z)',
        r'\s+nullable=.*?(?=\n\s+[a-z_]+=|\n    op\.|\n\n|\Z)',
    ]
    
    removed_count = 0
    
    for pattern in patterns_to_remove:
        matches = re.findall(pattern, content, re.MULTILINE)
        removed_count += len(matches)
        for match in matches:
            print(f"  Removing fragment: {repr(match)}")
            content = content.replace(match, '')
    
    # Clean up multiple consecutive newlines
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Fix any remaining syntax issues
    content = re.sub(r',\s*\n\s*\n\s*op\.', '\n\n    op.', content)
    
    print(f"\nTotal fragments removed: {removed_count}")
    
    # Write the cleaned migration file
    print("Writing cleaned migration file...")
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully fixed migration file corruption")

if __name__ == '__main__':
    fix_migration_corruption()
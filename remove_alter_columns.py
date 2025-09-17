#!/usr/bin/env python3
"""
Remove all alter column operations from migration to prevent dependency conflicts.
"""

import re

def remove_alter_columns():
    # Read the migration file
    migration_file = 'alembic/versions/20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'
    
    print("Reading migration file...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Removing all alter column operations...")
    
    # Track removed operations
    removed_count = 0
    
    # Remove all op.alter_column operations (multiline)
    patterns = [
        # Multi-line alter_column operations
        r'    op\.alter_column\([^)]*?\n(?:[^)]*?\n)*?[^)]*?\)',
        # Single-line alter_column operations  
        r'    op\.alter_column\([^)]*?\)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        removed_count += len(matches)
        for match in matches:
            print(f"  Removed: {match.split(chr(10))[0]}...")  # First line only
            content = content.replace(match, '')
    
    # Clean up any resulting empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    print(f"\nTotal alter column operations removed: {removed_count}")
    
    # Write the cleaned migration file
    print("Writing cleaned migration file...")
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully removed all alter column operations from migration file")

if __name__ == '__main__':
    remove_alter_columns()
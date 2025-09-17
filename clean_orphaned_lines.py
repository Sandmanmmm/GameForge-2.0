#!/usr/bin/env python3
"""Clean up orphaned lines from ALTER COLUMN fixes."""

import re

def clean_orphaned_lines():
    """Remove orphaned lines from incomplete ALTER COLUMN removals."""
    migration_file = "alembic/versions/20250917_1424_fc035ef6da47_add_all_missing_model_tables_with_.py"
    
    print(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Remove orphaned lines that were left behind from ALTER COLUMN operations
    orphaned_patterns = [
        r'\s*existing_nullable=False,\s*\n\s*existing_server_default=sa\.text\([^)]*\)\)\s*\n',
        r'\s*existing_nullable=False\)\s*\n',
        r'\s*existing_nullable=True\)\s*\n',
        r'\s*existing_type=[^,)]*,\s*\n\s*existing_nullable=[^)]*\)\s*\n',
        r'^\s*existing_nullable=[^)]*\)\s*$',
        r'^\s*existing_server_default=[^)]*\)\s*$',
    ]
    
    fixes_applied = 0
    
    for pattern in orphaned_patterns:
        matches = len(re.findall(pattern, content, re.MULTILINE))
        if matches > 0:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            fixes_applied += matches
            print(f"Removed {matches} orphaned lines matching pattern: {pattern[:30]}...")
    
    print(f"\nTotal orphaned lines removed: {fixes_applied}")
    
    # Write the cleaned migration
    with open(migration_file, 'w') as f:
        f.write(content)
    
    print(f"Migration file cleaned successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = clean_orphaned_lines()
    print(f"\nCompleted! Removed {fixes_applied} orphaned lines from migration file.")
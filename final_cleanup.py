#!/usr/bin/env python3
"""
Final comprehensive cleanup of migration file - remove all orphaned fragments.
"""

import re

def final_cleanup_migration():
    migration_file = 'alembic/versions/20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'
    
    print("Reading migration file...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("Removing orphaned fragments...")
    
    cleaned_lines = []
    removed_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip orphaned fragments
        if (stripped == ')' or 
            stripped.startswith('existing_nullable=') or
            stripped.startswith('existing_server_default=') or
            stripped.startswith('nullable=') or
            stripped.startswith('type_=') or
            stripped == ',' or
            stripped.startswith('autoincrement=') or
            stripped.startswith('server_default=')):
            print(f"  Removed orphaned fragment line {i+1}: {repr(stripped)}")
            removed_count += 1
            continue
        
        # Skip completely empty lines between op statements
        if stripped == '' and len(cleaned_lines) > 0 and cleaned_lines[-1].strip().startswith('op.'):
            next_non_empty = None
            for j in range(i+1, len(lines)):
                if lines[j].strip():
                    next_non_empty = lines[j].strip()
                    break
            if next_non_empty and next_non_empty.startswith('op.'):
                continue
        
        cleaned_lines.append(line)
    
    print(f"\nTotal orphaned fragments removed: {removed_count}")
    
    # Write the cleaned migration file
    print("Writing cleaned migration file...")
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print("✅ Successfully completed final cleanup of migration file")

if __name__ == '__main__':
    final_cleanup_migration()
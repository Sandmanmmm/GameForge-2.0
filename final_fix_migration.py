#!/usr/bin/env python3
"""
Final fix for migration file - ensure all op.add_column statements are properly closed.
"""

import re

def final_fix_migration():
    migration_file = 'alembic/versions/20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'
    
    print("Reading migration file...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Fixing incomplete op.add_column statements...")
    
    # Find incomplete op.add_column statements that are missing closing parentheses
    # Pattern: op.add_column('table', sa.Column('col', type, but no closing parentheses
    pattern = r"op\.add_column\('[^']+', sa\.Column\('[^']+', [^)]+(?:\([^)]*\))?(?:, [^)]+)*$"
    
    lines = content.split('\n')
    fixed_lines = []
    fixed_count = 0
    
    for i, line in enumerate(lines):
        # Check if this line is an incomplete op.add_column
        if re.match(r"\s*op\.add_column\(", line) and not line.strip().endswith('))'):
            # Check if it ends with a comma or incomplete parentheses
            stripped = line.strip()
            if stripped.endswith(',') or ',' in stripped:
                # Add the missing closing parentheses
                fixed_line = stripped.rstrip(',') + '))'
                fixed_lines.append(fixed_line)
                print(f"  Fixed line {i+1}: {stripped} -> {fixed_line}")
                fixed_count += 1
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Clean up any remaining issues
    content = re.sub(r',\s*\n\s*op\.', '\n    op.', content)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    print(f"\nTotal lines fixed: {fixed_count}")
    
    # Write the fixed migration file
    print("Writing fixed migration file...")
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully applied final fixes to migration file")

if __name__ == '__main__':
    final_fix_migration()
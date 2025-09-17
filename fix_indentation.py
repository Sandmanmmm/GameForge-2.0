#!/usr/bin/env python3
"""
Fix indentation errors in migration file.
"""

def fix_migration_indentation():
    migration_file = 'alembic/versions/20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'
    
    print("Reading migration file...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("Fixing indentation...")
    
    fixed_lines = []
    fixed_count = 0
    
    for i, line in enumerate(lines):
        # Check if this is a misindented op. statement
        if line.strip().startswith('op.') and not line.startswith('    '):
            # Fix indentation to 4 spaces
            fixed_line = '    ' + line.strip() + '\n'
            fixed_lines.append(fixed_line)
            if line.strip() != fixed_line.strip():
                print(f"  Fixed line {i+1}: {repr(line.strip())} -> proper indentation")
                fixed_count += 1
        else:
            fixed_lines.append(line)
    
    print(f"\nTotal lines fixed: {fixed_count}")
    
    # Write the fixed migration file
    print("Writing fixed migration file...")
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Successfully fixed migration file indentation")

if __name__ == '__main__':
    fix_migration_indentation()
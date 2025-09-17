#!/usr/bin/env python3
"""
Comprehensive UUID fix script for new migrations.
This script fixes all UUID type issues and dependency problems in one go.
"""

import re
import glob

def fix_new_migration():
    """Find and fix the latest migration file."""
    
    # Find the latest migration file
    migration_files = glob.glob("alembic/versions/*.py")
    if not migration_files:
        print("No migration files found!")
        return 0
    
    latest_migration = max(migration_files, key=lambda x: x.split('_')[1] if '_' in x else '0')
    print(f"Found latest migration: {latest_migration}")
    
    with open(latest_migration, 'r') as f:
        content = f.read()
    
    fixes_applied = 0
    
    # 1. Fix UUID types in table creation (String -> UUID)
    uuid_column_patterns = [
        (r"sa\.Column\('id', sa\.String\(\)", "sa.Column('id', postgresql.UUID(as_uuid=True)"),
        (r"sa\.Column\('([^']*_id)', sa\.String\(\)", r"sa.Column('\1', postgresql.UUID(as_uuid=True)"),
    ]
    
    print("Fixing UUID column types...")
    for pattern, replacement in uuid_column_patterns:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            fixes_applied += matches
            print(f"  Fixed {matches} UUID column instances")
    
    # 2. Add dependency fixes (constraint and view drops)
    if "op.drop_table('project_collaborators')" in content or "op.drop_table('game_templates')" in content:
        print("Adding dependency fixes...")
        
        # Find the first table drop operation and add view drops before it
        first_drop_match = re.search(r"(op\.drop_table\('[^']+'\))", content)
        if first_drop_match:
            # Add view drops before the first table drop
            content = re.sub(
                r"(op\.drop_table\('[^']+'\))",
                r"# Drop views that depend on tables we're about to drop\n    op.execute('DROP VIEW IF EXISTS project_stats CASCADE')\n    op.execute('DROP VIEW IF EXISTS user_stats CASCADE')\n    op.execute('DROP VIEW IF EXISTS migration_status CASCADE')\n    \n    \1",
                content,
                count=1  # Only replace the first occurrence
            )
            fixes_applied += 1
        
        # Add constraint drop before game_templates table drop if it exists
        if "op.drop_table('game_templates')" in content:
            content = re.sub(
                r"(op\.drop_table\('game_templates'\))",
                r"# Drop foreign key constraint before dropping the referenced table\n    op.drop_constraint(op.f('projects_template_id_fkey'), 'projects', type_='foreignkey')\n    \1",
                content
            )
            fixes_applied += 1
    
    # 3. Remove problematic ALTER COLUMN operations that convert UUID to String
    print("Removing problematic ALTER COLUMN operations...")
    alter_uuid_pattern = r"op\.alter_column\('(\w+)', '([^']*)',\s*\n\s*existing_type=sa\.UUID\(\),\s*\n\s*type_=sa\.String\(\),[^)]*\)"
    matches = len(re.findall(alter_uuid_pattern, content, re.MULTILINE | re.DOTALL))
    if matches > 0:
        content = re.sub(alter_uuid_pattern, r"# Keep \1.\2 as UUID - no alteration needed", content, flags=re.MULTILINE | re.DOTALL)
        fixes_applied += matches
        print(f"  Removed {matches} problematic ALTER COLUMN operations")
    
    # 4. Remove duplicate constraint drops
    if "op.drop_constraint(op.f('projects_template_id_fkey'), 'projects', type_='foreignkey')" in content:
        # Find and remove duplicate constraint drops
        parts = content.split("op.drop_constraint(op.f('projects_template_id_fkey'), 'projects', type_='foreignkey')")
        if len(parts) > 2:  # More than one occurrence
            # Keep only the first occurrence
            content = parts[0] + "op.drop_constraint(op.f('projects_template_id_fkey'), 'projects', type_='foreignkey')" + ''.join(parts[2:])
            fixes_applied += 1
            print("  Removed duplicate constraint drop")
    
    print(f"\nTotal fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(latest_migration, 'w') as f:
        f.write(content)
    
    print(f"Migration file {latest_migration} updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_new_migration()
    print(f"\nCompleted! Applied {fixes_applied} fixes to migration file.")
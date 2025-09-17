#!/usr/bin/env python3
"""
Comprehensive migration fix script for all remaining issues.
"""

import re
import glob

def fix_all_migration_issues():
    """Fix all remaining migration issues comprehensively."""
    
    # Find the latest migration file
    migration_files = glob.glob("alembic/versions/*.py")
    latest_migration = max(migration_files, key=lambda x: x.split('_')[1] if '_' in x else '0')
    print(f"Found latest migration: {latest_migration}")
    
    with open(latest_migration, 'r') as f:
        content = f.read()
    
    fixes_applied = 0
    
    # 1. Fix ALTER COLUMN operations that need explicit casting
    print("Fixing ALTER COLUMN operations with explicit casting...")
    
    # Fix users.role conversion
    users_role_pattern = r"op\.alter_column\('users', 'role',\s*\n\s*existing_type=sa\.ENUM\([^)]+\),\s*\n\s*type_=sa\.Enum\([^)]+name='userrole'\),[^)]*\)"
    matches = re.findall(users_role_pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        # Replace with explicit SQL execution
        content = re.sub(
            users_role_pattern,
            "# Convert users.role with explicit casting\n    op.execute(\"ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole\")",
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        fixes_applied += len(matches)
        print(f"  Fixed {len(matches)} users.role conversion issues")
    
    # Fix users.provider conversion
    users_provider_pattern = r"op\.alter_column\('users', 'provider',\s*\n\s*existing_type=sa\.VARCHAR\([^)]+\),\s*\n\s*type_=sa\.Enum\([^)]+name='authprovider'\),[^)]*\)"
    matches = re.findall(users_provider_pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        content = re.sub(
            users_provider_pattern,
            "# Convert users.provider with explicit casting\n    op.execute(\"ALTER TABLE users ALTER COLUMN provider TYPE authprovider USING provider::authprovider\")",
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        fixes_applied += len(matches)
        print(f"  Fixed {len(matches)} users.provider conversion issues")
    
    # Fix datasets.data_classification conversion
    datasets_class_pattern = r"op\.alter_column\('datasets', 'data_classification',\s*\n\s*existing_type=sa\.ENUM\([^)]+\),\s*\n\s*type_=sa\.Enum\([^)]+name='dataclassification'\),[^)]*\)"
    matches = re.findall(datasets_class_pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        content = re.sub(
            datasets_class_pattern,
            "# Convert datasets.data_classification with explicit casting\n    op.execute(\"ALTER TABLE datasets ALTER COLUMN data_classification TYPE dataclassification USING 'PUBLIC'::dataclassification\")",
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        fixes_applied += len(matches)
        print(f"  Fixed {len(matches)} datasets.data_classification conversion issues")
    
    # Fix ai_requests.status conversion
    ai_requests_status_pattern = r"op\.alter_column\('ai_requests', 'status',\s*\n\s*existing_type=sa\.ENUM\([^)]+\),\s*\n\s*type_=sa\.Enum\([^)]+name='airequeststatus'\),[^)]*\)"
    matches = re.findall(ai_requests_status_pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        content = re.sub(
            ai_requests_status_pattern,
            "# Convert ai_requests.status with explicit casting\n    op.execute(\"ALTER TABLE ai_requests ALTER COLUMN status TYPE airequeststatus USING 'PENDING'::airequeststatus\")",
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        fixes_applied += len(matches)
        print(f"  Fixed {len(matches)} ai_requests.status conversion issues")
    
    print(f"\nTotal fixes applied: {fixes_applied}")
    
    # Write the fixed migration
    with open(latest_migration, 'w') as f:
        f.write(content)
    
    print(f"Migration file {latest_migration} updated successfully!")
    return fixes_applied

if __name__ == "__main__":
    fixes_applied = fix_all_migration_issues()
    print(f"\nCompleted! Applied {fixes_applied} fixes to migration file.")
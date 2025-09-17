#!/usr/bin/env python3
"""
Script to fix UUID foreign key types in Alembic migration file
"""
import re

# Define the list of foreign key column names that reference UUID primary keys
uuid_foreign_keys = [
    'user_id', 'creator_id', 'owner_id', 'project_id', 'template_id', 'category_id',
    'asset_id', 'dataset_id', 'experiment_id', 'model_id', 'base_model_id', 
    'training_dataset_id', 'validation_dataset_id', 'test_dataset_id', 
    'parent_id', 'parent_comment_id', 'parent_version_id', 'parent_event_id',
    'previous_version_id', 'thread_root_id', 'author_id', 'buyer_id', 
    'invited_by_id', 'invited_user_id', 'purchase_id', 'model_version_id',
    'api_key_id', 'comment_id', 'created_by_id', 'organization_id',
    'target_user_id', 'sender_id', 'resource_id', 'scope_id',
    'reference_dataset_id'
]

# Additional non-UUID foreign keys (external IDs that should stay as String)
external_string_keys = [
    'payment_method_id', 'invoice_id', 'external_subscription_id', 
    'external_customer_id'
]

migration_file = r'alembic\versions\20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'

print("Reading migration file...")
with open(migration_file, 'r') as f:
    content = f.read()

print("Applying UUID foreign key fixes...")
changes_made = 0

# First fix primary key IDs
pattern = r"sa\.Column\('id', sa\.String\(\)"
replacement = "sa.Column('id', postgresql.UUID(as_uuid=True)"

old_content = content
content = re.sub(pattern, replacement, content)

if old_content != content:
    matches = len(re.findall(pattern, old_content))
    changes_made += matches
    print(f"  Fixed {matches} instances of 'id' primary key")

# Then fix UUID foreign keys
for fk in uuid_foreign_keys:
    # Pattern: sa.Column('foreign_key_name', sa.String(), ...
    pattern = rf"sa\.Column\('{fk}', sa\.String\(\)"
    replacement = f"sa.Column('{fk}', postgresql.UUID(as_uuid=True)"
    
    old_content = content
    content = re.sub(pattern, replacement, content)
    
    if old_content != content:
        matches = len(re.findall(pattern, old_content))
        changes_made += matches
        print(f"  Fixed {matches} instances of '{fk}'")

print(f"\nTotal changes made: {changes_made}")

if changes_made > 0:
    print("Writing updated migration file...")
    with open(migration_file, 'w') as f:
        f.write(content)
    print("✅ Successfully updated all UUID foreign key types in migration file")
else:
    print("⚠️ No changes were needed")
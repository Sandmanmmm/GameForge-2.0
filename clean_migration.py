#!/usr/bin/env python3
"""
Script to remove all drop operations from Alembic migration file
"""
import re

migration_file = r'alembic\versions\20250917_1410_ddd7ef1e76af_add_all_missing_model_tables_with_.py'

print("Reading migration file...")
with open(migration_file, 'r') as f:
    content = f.read()

print("Removing all drop operations...")
original_lines = content.split('\n')
filtered_lines = []
drop_operations_removed = 0

for line in original_lines:
    stripped_line = line.strip()
    
    # Skip lines that contain drop operations
    if (stripped_line.startswith('op.drop_table') or 
        stripped_line.startswith('op.drop_index') or
        stripped_line.startswith('op.drop_column') or
        stripped_line.startswith('op.drop_constraint') or
        stripped_line.startswith('# op.drop_table')):
        
        drop_operations_removed += 1
        print(f"  Removed: {stripped_line}")
        continue
    
    filtered_lines.append(line)

# Rejoin the content
content = '\n'.join(filtered_lines)

print(f"\nTotal drop operations removed: {drop_operations_removed}")

if drop_operations_removed > 0:
    print("Writing cleaned migration file...")
    with open(migration_file, 'w') as f:
        f.write(content)
    print("✅ Successfully removed all drop operations from migration file")
else:
    print("⚠️ No drop operations found to remove")
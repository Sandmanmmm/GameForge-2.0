"""
Test file to isolate the import issue.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test imports step by step
print("1. Importing base...")
from gameforge.core.base import Base

print("2. Importing data classification...")
from gameforge.core.data_classification import DataClassification

print("3. Testing basic SQLAlchemy...")
from sqlalchemy import Column, String

print("4. All imports successful!")
print(f"Base: {Base}")
print(f"DataClassification: {DataClassification}")
#!/usr/bin/env python3
"""
Test script to verify all models can be imported successfully after UUID conversion.
"""

import sys
import traceback

def test_model_imports():
    """Test importing all model modules."""
    print("Testing model imports...")
    
    model_modules = [
        'gameforge.models.users',
        'gameforge.models.projects', 
        'gameforge.models.collaboration',
        'gameforge.models.ai_ml',
        'gameforge.models.system',
        'gameforge.models.enterprise'
    ]
    
    success_count = 0
    failed_imports = []
    
    for module in model_modules:
        try:
            print(f"  Importing {module}...", end=' ')
            __import__(module)
            print("✅ SUCCESS")
            success_count += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed_imports.append((module, str(e), traceback.format_exc()))
    
    print(f"\nImport Results:")
    print(f"  ✅ Successful: {success_count}/{len(model_modules)}")
    print(f"  ❌ Failed: {len(failed_imports)}/{len(model_modules)}")
    
    if failed_imports:
        print("\nFailed Import Details:")
        for module, error, tb in failed_imports:
            print(f"\n{'='*60}")
            print(f"Module: {module}")
            print(f"Error: {error}")
            print("Traceback:")
            print(tb)
    
    return len(failed_imports) == 0

if __name__ == "__main__":
    success = test_model_imports()
    sys.exit(0 if success else 1)
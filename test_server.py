#!/usr/bin/env python3
"""
Minimal server to test registration endpoint specifically.
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from gameforge.app import app

if __name__ == "__main__":
    print("🚀 Starting minimal GameForge server for registration test...")
    print("📝 Testing endpoint: POST /api/v1/auth/register")
    print("🔍 Check server logs for registration attempts")
    print("-" * 50)
    
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8080,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
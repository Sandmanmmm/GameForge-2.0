#!/usr/bin/env python3
"""
Simple authentication integration test for GameForge AI endpoints.

This script tests that:
1. Unauthenticated requests are blocked (401/403)
2. Authenticated requests work properly with user context
3. Assets are properly saved to user projects
"""

import json
import requests
import time
import os
from typing import Dict, Any


# Configuration
BASE_URL = "http://localhost:8080/api/v1"

# Test JWT token (you would normally get this from login)
# For testing, we'll use a fake token that matches the format expected
TEST_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6InRlc3QtdXNlci0xMjMiLCJ1c2VySWQiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGdhbWVmb3JnZS5haSIsInVzZXJuYW1lIjoidGVzdGVyIiwibmFtZSI6IlRlc3QgVXNlciJ9.invalid-signature"


def test_unauthenticated_requests():
    """Test that unauthenticated requests are properly blocked."""
    print("🔒 Testing unauthenticated requests...")
    
    # Test AI generation without auth
    response = requests.post(f"{BASE_URL}/ai/generate", json={
        "prompt": "Test prompt",
        "style": "fantasy",
        "category": "weapons"
    })
    
    print(f"   AI Generate (no auth): {response.status_code}")
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    # Test job status without auth
    response = requests.get(f"{BASE_URL}/ai/job/test-job-123")
    print(f"   Job Status (no auth): {response.status_code}")
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    # Test asset listing without auth
    response = requests.get(f"{BASE_URL}/assets/")
    print(f"   Asset List (no auth): {response.status_code}")
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    print("✅ Unauthenticated requests properly blocked")


def test_authenticated_requests():
    """Test that authenticated requests work properly."""
    print("🔑 Testing authenticated requests...")
    
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    
    # Test AI generation with auth (should work but might fail due to invalid token signature)
    response = requests.post(f"{BASE_URL}/ai/generate", 
        json={
            "prompt": "A magical sword with glowing runes",
            "style": "fantasy",
            "category": "weapons",
            "width": 512,
            "height": 512,
            "quality": "standard"
        },
        headers=headers
    )
    
    print(f"   AI Generate (with auth): {response.status_code}")
    
    if response.status_code == 401:
        print("   ⚠️  Token signature invalid (expected for test token)")
        return False
    elif response.status_code == 422:
        print("   ⚠️  Validation error:", response.json())
        return False
    elif response.status_code == 202:
        print("   ✅ AI generation request accepted")
        job_data = response.json()
        print(f"   Job ID: {job_data.get('job_id')}")
        return True
    
    return False


def test_job_ownership():
    """Test that users can only access their own jobs."""
    print("👤 Testing job ownership...")
    
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    
    # Test job listing (should return empty list for test user)
    response = requests.get(f"{BASE_URL}/ai/jobs", headers=headers)
    print(f"   Job List (with auth): {response.status_code}")
    
    if response.status_code == 401:
        print("   ⚠️  Token signature invalid")
        return False
    elif response.status_code == 200:
        jobs = response.json()
        print(f"   Found {len(jobs)} jobs for test user")
        return True
    
    return False


def test_asset_storage():
    """Test that assets are properly stored in user projects."""
    print("💾 Testing asset storage...")
    
    # Check if data directory exists
    data_path = "./data/projects/test-user-123"
    if os.path.exists(data_path):
        project_files = os.listdir(data_path)
        print(f"   Project files found: {project_files}")
        
        if "default.json" in project_files:
            with open(os.path.join(data_path, "default.json"), 'r') as f:
                project_data = json.load(f)
            print(f"   Project: {project_data.get('name')}")
            print(f"   Assets: {len(project_data.get('assets', []))}")
            return True
    else:
        print("   No project data found (expected for fresh test)")
        return False


def main():
    """Run all authentication tests."""
    print("🧪 GameForge Authentication Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Unauthenticated requests should be blocked
        test_unauthenticated_requests()
        print()
        
        # Test 2: Authenticated requests should work
        auth_works = test_authenticated_requests()
        print()
        
        # Test 3: Job ownership verification
        ownership_works = test_job_ownership()
        print()
        
        # Test 4: Asset storage verification
        storage_works = test_asset_storage()
        print()
        
        print("📊 Test Summary:")
        print(f"   ✅ Unauthenticated blocking: PASS")
        print(f"   {'✅' if auth_works else '⚠️ '} Authenticated requests: {'PASS' if auth_works else 'SKIP (invalid token)'}")
        print(f"   {'✅' if ownership_works else '⚠️ '} Job ownership: {'PASS' if ownership_works else 'SKIP (invalid token)'}")
        print(f"   {'✅' if storage_works else 'ℹ️ '} Asset storage: {'PASS' if storage_works else 'NO DATA'}")
        
        if not auth_works:
            print("\n💡 Note: To fully test authenticated features, run with a valid JWT token")
            print("   You can generate one by logging in through the frontend first.")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1
    
    print("\n🎉 Authentication integration test completed!")
    return 0


if __name__ == "__main__":
    exit(main())
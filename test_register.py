#!/usr/bin/env python3
"""
Simple test script to verify the registration endpoint works.
"""
import requests
import json


def test_registration():
    """Test the registration endpoint"""
    url = "http://localhost:8080/api/v1/auth/register"
    
    # Test data
    test_user = {
        "username": "testuser123",
        "email": "testuser123@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    
    print(f"Testing registration endpoint: {url}")
    print(f"Test data: {json.dumps(test_user, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.content:
            try:
                response_json = response.json()
                print(f"Response JSON: {json.dumps(response_json, indent=2)}")
            except Exception:
                print(f"Response Text: {response.text}")
        else:
            print("No response content")
            
        if response.status_code == 201:
            print("✅ Registration successful!")
        elif response.status_code == 409:
            print("⚠️ User already exists - "
                  "this is expected if running multiple times")
        else:
            print(f"❌ Registration failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. "
              "Make sure it's running on port 8080.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_registration()
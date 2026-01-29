import requests
import json

base_url = "http://localhost:8000"

# Register a new user
payload = {
    "name": "Test User",
    "email": "testuser@example.com",
    "password": "password123",
    "phone": "1234567890"
}

try:
    response = requests.post(f"{base_url}/auth/signup", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"User registered successfully.")
        print(f"Role: {data['user']['role']}")
        if data['user']['role'] == 'user':
            print("✅ Verification Passed: Default role is 'user'.")
        else:
            print(f"❌ Verification Failed: Expected 'user', got '{data['user']['role']}'.")
    else:
        print(f"❌ Registration failed: {response.text}")

except Exception as e:
    print(f"Error: {e}")

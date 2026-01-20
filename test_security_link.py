
import sys
import os
import asyncio
import requests
from core.security import generate_signed_url_params
from core.database import SessionLocal, MediaRecord

def test_link_gen():
    print("--- Testing Link Generation ---")
    s_id = "test_source_123"
    params = generate_signed_url_params(s_id)
    print(f"Params: {params}")
    
    # Validation URL
    url = f"http://127.0.0.1:8000/api/mobile/metadata?id={params['id']}&sign={params['sign']}&expires={params['expires']}"
    print(f"URL: {url}")
    
    return params

def test_api_access(params):
    print("\n--- Testing API Access ---")
    # For this to work, server must be running and have a record satisfying the ID?
    # Or at least return 404 (which means Auth passed).
    # If Auth fails, it returns 403.
    
    res = requests.get(f"http://127.0.0.1:8000/api/mobile/metadata", params=params)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
    
    if res.status_code == 403:
        print("FAIL: Auth failed!")
    elif res.status_code == 404:
        print("SUCCESS: Auth passed (Song not found is expected)")
    elif res.status_code == 200:
        print("SUCCESS: Data retrieved")
        
def test_expiry():
    print("\n--- Testing Expiry ---")
    from core.security import generate_signed_url_params
    # Generate expired link
    params = generate_signed_url_params("expired_id", -100)
    res = requests.get(f"http://127.0.0.1:8000/api/mobile/metadata", params=params)
    print(f"Status (Expired): {res.status_code}")
    if res.status_code == 403:
        print("SUCCESS: Expired link rejected")
    else:
        print("FAIL: Expired link accepted or other error")

if __name__ == "__main__":
    # Ensure we run this while server is UP.
    try:
        p = test_link_gen()
        test_api_access(p)
        test_expiry()
    except Exception as e:
        print(e)

import requests
import json

url = "http://127.0.0.1:8000/api/artists"
payload = {
    "name": "李剑青",
    "source": "qqmusic",
    "id": "000QF68J1y5K7w",
    "avatar": ""
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

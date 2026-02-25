import requests
import json

url = "https://ark.cn-beijing.volces.com/api/v3/videos/generations"
headers = {
    "Authorization": "Bearer test_key",
    "Content-Type": "application/json"
}
payload = {
    "model": "doubao-seedance-1-5-pro-251215",
    "prompt": "test",
    "resolution": "720p",
    "duration": 5
}

print(f"Testing POST to {url}")

# Test 2: Proxies disabled via argument (same as node code)
print("\n--- Test 2: proxies={'http': None, 'https': None} ---")
try:
    resp = requests.post(url, headers=headers, json=payload, timeout=10, proxies={"http": None, "https": None})
    print(f"Success! Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Failed: {e}")

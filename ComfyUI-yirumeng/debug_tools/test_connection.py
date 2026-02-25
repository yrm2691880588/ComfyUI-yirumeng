import requests
import os
import sys

url = "https://ark.cn-beijing.volces.com"

print(f"Testing connection to {url}")
print(f"Environment proxies: HTTP_PROXY={os.environ.get('HTTP_PROXY')}, HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")

# Test 1: Default (uses env proxies if set)
print("\n--- Test 1: Default requests.get ---")
try:
    resp = requests.get(url, timeout=10)
    print(f"Success! Status: {resp.status_code}")
except Exception as e:
    print(f"Failed: {e}")

# Test 2: Proxies disabled via argument
print("\n--- Test 2: proxies={'http': None, 'https': None} ---")
try:
    resp = requests.get(url, timeout=10, proxies={"http": None, "https": None})
    print(f"Success! Status: {resp.status_code}")
except Exception as e:
    print(f"Failed: {e}")

# Test 3: Session with trust_env=False
print("\n--- Test 3: Session(trust_env=False) ---")
try:
    s = requests.Session()
    s.trust_env = False
    resp = s.get(url, timeout=10)
    print(f"Success! Status: {resp.status_code}")
except Exception as e:
    print(f"Failed: {e}")

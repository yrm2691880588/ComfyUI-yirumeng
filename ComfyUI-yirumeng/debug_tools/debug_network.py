import socket
import sys
import os
import requests
import urllib.request
import ssl

print(f"Python Version: {sys.version}")
print(f"Socket Default Timeout: {socket.getdefaulttimeout()}")

target_host = "ark.cn-beijing.volces.com"
target_url = f"https://{target_host}/api/v3/videos/generations"

print(f"\n--- 1. DNS Resolution Check for {target_host} ---")
try:
    ip_list = socket.getaddrinfo(target_host, 443)
    print(f"Success. IPs found: {ip_list}")
except Exception as e:
    print(f"DNS Resolution Failed: {e}")

print(f"\n--- 2. Socket Connect Check (Port 443) ---")
try:
    s = socket.create_connection((target_host, 443), timeout=5)
    print("Socket connection successful!")
    s.close()
except Exception as e:
    print(f"Socket Connection Failed: {e}")

print(f"\n--- 3. Urllib Check (Standard Library) ---")
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
        print(f"Urllib Success! Status: {response.status}")
except Exception as e:
    print(f"Urllib Failed: {e}")

print(f"\n--- 4. Requests Check (No Proxy, No Verify) ---")
try:
    s = requests.Session()
    s.trust_env = False
    resp = s.get(target_url, verify=False, timeout=10)
    print(f"Requests Success! Status: {resp.status_code}")
except Exception as e:
    print(f"Requests Failed: {e}")

print(f"\n--- 5. Environment Variables ---")
print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

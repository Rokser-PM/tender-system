import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import requests

BASE = "https://www.tenders.co.il"

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9",
    "Origin": BASE,
    "Referer": f"{BASE}/login",
    "Content-Type": "application/json",
})

# Step 1: Get initial cookies
r0 = sess.get(f"{BASE}/login", timeout=15)
print(f"Initial GET: {r0.status_code}")
print(f"Cookies after GET: {dict(sess.cookies)}")

# Step 2: Login
r = sess.post(f"{BASE}/Data/api/Account/Login",
              json={"UserName": "0523661388", "Password": "0523661388", "RememberMe": True},
              timeout=15)
print(f"\nLogin: {r.status_code}")
print(f"Response body: {r.text[:300]}")
print(f"Response headers: {dict(r.headers)}")
print(f"Cookies after login: {list(sess.cookies.keys())}")

# Step 3: Try API with all cookies + headers
sess.headers.update({
    "Referer": f"{BASE}/main",
    "X-Requested-With": "XMLHttpRequest",
})
r2 = sess.get(f"{BASE}/Data/api/Account/Me", timeout=15)
print(f"\n/Me: {r2.status_code} | {r2.text[:200]}")

r3 = sess.get(f"{BASE}/Data/api/Agent/GetAgentResults?page=1&pageSize=10", timeout=15)
print(f"\nGetAgentResults: {r3.status_code} | {r3.text[:300]}")

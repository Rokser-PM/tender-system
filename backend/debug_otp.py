import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
import requests

BASE = "https://www.tenders.co.il"

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": BASE,
    "Referer": f"{BASE}/login",
})

# Login
sess.get(f"{BASE}/login", timeout=15)
r = sess.post(f"{BASE}/Data/api/Account/Login",
              json={"UserName": "0523661388", "Password": "0523661388", "RememberMe": True},
              timeout=15)
data = r.json()
token = data.get("Token", "")
need_otp = data.get("NeedOtp", False)
print(f"NeedOtp: {need_otp}")
print(f"Token: {token[:50]}...")

# נסה Bearer token ישירות
sess.headers["Authorization"] = f"Bearer {token}"
sess.headers["Referer"] = f"{BASE}/main"
sess.headers["X-Requested-With"] = "XMLHttpRequest"

r2 = sess.get(f"{BASE}/Data/api/Account/Me", timeout=15)
print(f"\n/Me with Bearer: {r2.status_code} | {r2.text[:100]}")

r3 = sess.get(f"{BASE}/Data/api/Agent/GetAgentResults?page=1&pageSize=5", timeout=15)
print(f"GetAgentResults: {r3.status_code} | {r3.text[:200]}")

# חפש endpoint של OTP
for endpoint in [
    "/Data/api/Account/VerifyOtp",
    "/Data/api/Account/OtpVerification",
    "/Data/api/Account/Verify",
    "/Data/api/Account/ConfirmOtp",
]:
    r_test = sess.get(f"{BASE}{endpoint}", timeout=5)
    if r_test.status_code != 404:
        print(f"Found: {endpoint} -> {r_test.status_code}")

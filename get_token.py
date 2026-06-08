"""
הפעל אחת מהמחשב הביתי כדי לקבל JWT token לשימוש ב-Render.
python get_token.py
"""
import os, sys, requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

BASE = "https://www.tenders.co.il"

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

env = load_env()
phone = input(f"טלפון [{env.get('TENDERS_PHONE', '')}]: ").strip() or env.get("TENDERS_PHONE", "")
password = input(f"סיסמא [{env.get('TENDERS_PASSWORD', '')}]: ").strip() or env.get("TENDERS_PASSWORD", "")

sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": BASE,
    "Referer": f"{BASE}/login",
})

print("\nשולח בקשת כניסה...")
sess.get(f"{BASE}/login", timeout=10)
r = sess.post(
    f"{BASE}/Data/api/Account/Login",
    json={"UserName": phone, "Password": password, "RememberMe": True},
    timeout=15
)

print(f"תגובת שרת: {r.status_code}")
data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}

# אם צריך OTP
if data.get("RequiresTwoFactor") or data.get("requiresTwoFactor") or not data.get("Token"):
    print("נשלח SMS לטלפון שלך. הכנס את הקוד:")
    otp = input("קוד SMS: ").strip()

    # נסה endpoint של OTP
    for otp_url in [
        f"{BASE}/Data/api/Account/VerifyOTP",
        f"{BASE}/Data/api/Account/TwoFactor",
        f"{BASE}/Data/api/Account/LoginOTP",
    ]:
        r2 = sess.post(otp_url, json={"Code": otp, "UserName": phone, "RememberMe": True}, timeout=15)
        if r2.status_code == 200:
            data2 = r2.json()
            if data2.get("Token"):
                data = data2
                break
        print(f"  {otp_url}: {r2.status_code}")

token = data.get("Token", "") or data.get("token", "") or data.get("access_token", "")

if token:
    print(f"\n✅ TOKEN הושג בהצלחה!\n")
    print("=" * 60)
    print(token)
    print("=" * 60)
    print("\nעכשיו:")
    print("1. עבור ל-Render Dashboard -> השירות שלך -> Environment")
    print("2. הוסף משתנה חדש: TENDERS_JWT_TOKEN")
    print("3. הדבק את ה-token למעלה")
    print("4. לחץ Save Changes")

    # שמור גם קובץ מקומי
    with open(os.path.join(os.path.dirname(__file__), "backend", "data", "jwt_token.txt"), "w") as f:
        f.write(token)
    print("\nToken נשמר גם ל-backend/data/jwt_token.txt")
else:
    print(f"\n❌ לא הצלחנו לקבל token")
    print(f"תגובה: {r.text[:300]}")

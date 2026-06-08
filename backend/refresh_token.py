"""
מתחבר ליפעת דרך Playwright ושומר JWT Token + Cookies.
"""
import sys, os, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jwt_token.txt")
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "tenders_cookies.txt")
BASE = "https://www.tenders.co.il"


def load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8-sig") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env[k.strip()] = v.strip()
    return env


env = load_env()
phone = env.get("TENDERS_PHONE", "")
password = env.get("TENDERS_PASSWORD", "")

print("פותח דפדפן ליפעת מכרזים...")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    captured_token = {"value": None}
    all_json_responses = []

    def on_request(request):
        """לכוד JWT מכותרת Authorization."""
        if captured_token["value"]:
            return
        try:
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                t = auth.split(" ", 1)[1].strip()
                if t and len(t) > 50 and t.startswith("eyJ"):
                    captured_token["value"] = t
                    print(f"\n[+] Token מ-request header! ({len(t)} תווים)")
        except Exception:
            pass

    def on_response(response):
        """לכוד JWT מ-response body."""
        if captured_token["value"]:
            return
        try:
            url = response.url
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = response.text()
            if not body or len(body) < 5:
                return

            # לוג כל response מה-API
            if "/Data/api/" in url or "/api/" in url.lower():
                snippet = body[:150].replace("\n", " ")
                print(f"    [API] {url.split('/')[-1]}: {snippet}")

            # חפש JWT
            if '"Token"' in body or '"token"' in body or '"jwt"' in body:
                try:
                    data = json.loads(body)
                    for key in ["Token", "token", "AccessToken", "access_token", "jwt"]:
                        t = data.get(key, "")
                        if t and isinstance(t, str) and len(t) > 50 and t.startswith("eyJ"):
                            captured_token["value"] = t
                            print(f"\n[+] Token מ-response ({url})! ({len(t)} תווים)")
                            return
                except Exception:
                    pass
        except Exception:
            pass

    page.on("request", on_request)
    page.on("response", on_response)

    # פתח דף הבית
    page.goto(f"{BASE}/home", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # סגור popup עוגיות
    try:
        ok = page.query_selector('button:has-text("אישור")')
        if ok:
            ok.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    # לחץ "כניסה למנויים" לפתיחת modal הכניסה
    try:
        login_link = page.query_selector('a:has-text("כניסה למנויים")')
        if login_link:
            login_link.click()
            page.wait_for_timeout(2000)
            print("[+] Modal כניסה נפתח")
        else:
            print("[!] קישור 'כניסה למנויים' לא נמצא")
    except Exception as e:
        print(f"[!] שגיאת פתיחת modal: {e}")

    # מלא שם משתמש וסיסמה
    try:
        user_field = page.query_selector('input[name="userName"]')
        if user_field:
            user_field.fill(phone)
            print(f"[+] שם משתמש הוזן ({phone})")
        else:
            print("[!] שדה userName לא נמצא")

        pass_field = page.query_selector('input[name="password"]')
        if pass_field:
            pass_field.fill(password)
            print("[+] סיסמה הוזנה")
        else:
            print("[!] שדה password לא נמצא")

        # ודא שה-toggle OTP מייל כבוי
        otp_toggle = page.query_selector('input[name="rememberMe"] ~ * input[type="checkbox"], .toggle input, input[type="checkbox"][name*="otp"]')
        # נסה לכבות אם דלוק
        # (ניגש לפי ה-screenshot — toggle כנראה כבוי כברירת מחדל)

        # לחץ התחברות
        submit_btn = page.query_selector('button:has-text("התחברות")')
        if submit_btn:
            submit_btn.click()
            print("[+] כפתור התחברות לחוץ")
        else:
            page.keyboard.press("Enter")
            print("[+] Enter נשלח")
    except Exception as e:
        print(f"[!] Auto-fill error: {e}")

    print()
    print("=" * 60)
    print(">> אם מופיעה תיבת קוד SMS — הכנס את הקוד בדפדפן!")
    print("   הסקריפט ימתין עד 4 דקות.")
    print("=" * 60)
    print()

    # המתן — אל תנווט לשום מקום!
    for i in range(240):
        page.wait_for_timeout(1000)

        if captured_token["value"]:
            break

        # בדיקת URL בכל 10 שניות
        if i % 10 == 0:
            current = page.url
            print(f"[{i:3d}s] URL: {current.replace(BASE, '')}")

    # שמור עוגיות בכל מקרה
    try:
        cookies = context.cookies()
        relevant = [c for c in cookies if "tenders" in c.get("domain", "").lower()]
        if relevant:
            os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                for c in relevant:
                    f.write(f"{c['name']}={c['value']}\n")
            print(f"\n[+] {len(relevant)} עוגיות נשמרו")
        else:
            print("\n[!] לא נמצאו עוגיות לשמירה")
    except Exception as e:
        print(f"[!] שגיאת עוגיות: {e}")

    browser.close()

    if captured_token["value"]:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(captured_token["value"])
        print(f"[OK] Token נשמר! ({len(captured_token['value'])} תווים)")
        print("המערכת מוכנה — הפעל start.bat")
    else:
        print()
        print("[X] Token לא נלכד.")
        print()
        print("פתרון ידני:")
        print("1. פתח Edge עם tenders.co.il מחובר")
        print("2. לחץ F12 > Network > רענן דף")
        print("3. חפש request ל-api/Account/Me או api/Agent")
        print("4. לחץ על הבקשה > Headers > Authorization: Bearer eyJ...")
        print("5. העתק את הטוקן (ה-eyJ...) ושמור ב:")
        print(f"   {TOKEN_FILE}")

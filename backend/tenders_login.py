"""
התחברות ל-tenders.co.il עם JWT Token — ללא OTP.
מחזיר רשימת כל המכרזים מהסוכן האישי.
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))
import requests

BASE = "https://www.tenders.co.il"
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
TOKEN_FILE = os.path.join(DATA_DIR, "jwt_token.txt")


def load_env() -> dict:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def get_jwt_token(allow_relogin: bool = True) -> str | None:
    """מחזיר JWT token — מ-cache בלבד (ללא login אוטומטי שמשלח SMS)."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
        if token and is_token_valid(token):
            return token

    # אם הטוקן פג — רק אם ביקשו במפורש
    if allow_relogin:
        print("JWT token expired — refreshing...")
        return login_and_get_token()

    print("JWT token expired — skipping (no SMS)")
    return None


def is_token_valid(token: str) -> bool:
    """בודק אם ה-token עדיין בתוקף."""
    try:
        r = requests.get(
            f"{BASE}/Data/api/Account/Me",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def login_and_get_token() -> str | None:
    """מתחבר ומחזיר JWT token."""
    env = load_env()
    phone = env.get("TENDERS_PHONE", "")
    password = env.get("TENDERS_PASSWORD", "")

    if not phone or not password:
        print("חסרים פרטי כניסה ב-.env")
        return None

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": BASE,
        "Referer": f"{BASE}/login",
    })

    try:
        sess.get(f"{BASE}/login", timeout=10)
        r = sess.post(
            f"{BASE}/Data/api/Account/Login",
            json={"UserName": phone, "Password": password, "RememberMe": True},
            timeout=15
        )
        if r.status_code == 200:
            token = r.json().get("Token", "")
            if token:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(TOKEN_FILE, "w") as f:
                    f.write(token)
                print("התחברות הצליחה — JWT token נשמר")
                return token
        print(f"Login failed: {r.status_code} — {r.text[:100]}")
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None


def make_api_session(token: str) -> requests.Session:
    """יוצר session עם Bearer token."""
    sess = requests.Session()
    sess.headers.update({
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/main",
    })
    return sess


def fetch_my_tenders(max_pages: int = 5) -> list[dict]:
    """מחזיר את כל המכרזים מהסוכן — עמוד עמוד."""
    token = get_jwt_token()
    if not token:
        return []

    sess = make_api_session(token)
    all_tenders = []

    for page in range(1, max_pages + 1):
        try:
            r = sess.get(
                f"{BASE}/Data/api/Agent/GetAgentResults?page={page}&pageSize=50",
                timeout=15
            )
            if r.status_code == 401:
                # Token פג — התחבר שוב
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                token = login_and_get_token()
                if not token:
                    break
                sess = make_api_session(token)
                r = sess.get(
                    f"{BASE}/Data/api/Agent/GetAgentResults?page={page}&pageSize=50",
                    timeout=15
                )

            if r.status_code != 200:
                break

            data = r.json()
            items = data.get("data", []) if isinstance(data, dict) else data
            if not items:
                break

            all_tenders.extend(items)
            total = data.get("info", {}).get("count", 0) if isinstance(data, dict) else len(items)
            print(f"  עמוד {page}: {len(items)} מכרזים (סה\"כ: {total})")

            if len(all_tenders) >= total or len(items) < 50:
                break

        except Exception as e:
            print(f"Error page {page}: {e}")
            break

    return all_tenders


def tender_to_url(tender: dict) -> str:
    """ממיר נתוני מכרז ל-URL — משתמש ב-EncID (כתובת אמיתית של יפעת)."""
    enc_id = tender.get("EncID") or tender.get("encId") or tender.get("enc_id")
    if enc_id:
        return f"{BASE}/tender/{enc_id}"
    # Fallback לשדות אחרים
    for field in ["Url", "url", "URL", "Link", "link"]:
        if tender.get(field) and str(tender[field]).startswith("http"):
            return tender[field]
    # אחרון — ID מספרי (פחות מועדף)
    tid = tender.get("TenderID") or tender.get("Id") or tender.get("id")
    if tid:
        return f"{BASE}/tender/{tid}"
    return ""


def get_tender_urls() -> list[str]:
    """מחזיר URLs של כל המכרזים."""
    tenders = fetch_my_tenders()
    urls = []
    for t in tenders:
        url = tender_to_url(t)
        if url:
            urls.append(url)
    return urls


def get_full_tender_list() -> list[dict]:
    """מחזיר רשימה מלאה עם כל הנתונים."""
    tenders = fetch_my_tenders()
    result = []
    for t in tenders:
        result.append({
            "tender_id": str(t.get("TenderID", t.get("Id", ""))),
            "url": tender_to_url(t),
            "title": t.get("Title", ""),
            "publisher": t.get("PublisherName", t.get("Publisher", "")),
            "branch": t.get("SubjectName", t.get("Subject", "")),
            "tender_type": t.get("TenderType", t.get("Type", "")),
            "submission_date": t.get("InfoDate", t.get("SubmissionDate", "")),
            "description": t.get("Description", ""),
            "documents": [],
        })
    return result


if __name__ == "__main__":
    print("=== בדיקת API של tenders.co.il ===")
    tenders = get_full_tender_list()
    print(f"\nסה\"כ מכרזים: {len(tenders)}")
    for t in tenders[:5]:
        print(f"  [{t['tender_id']}] {t['title'][:50]}")
        print(f"    מפרסם: {t['publisher']} | תאריך: {t['submission_date']}")
        print(f"    URL: {t['url'][:70]}")

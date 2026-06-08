"""
Scraper שמשתמש ב-Playwright עם Chromium + קוקיות מהקובץ.
עובד גם כש-Chrome פתוח ברקע.
"""
import os
import json
import re
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DOCS_DIR = os.path.join(DATA_DIR, "documents")


def load_cookies() -> list[dict]:
    """טוען קוקיות מהקובץ לפורמט Playwright."""
    cookie_file = os.path.join(DATA_DIR, "tenders_cookies.txt")
    cookies = []
    if not os.path.exists(cookie_file):
        return cookies
    with open(cookie_file, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # Playwright cookie format
            cookies.append({
                "name": k,
                "value": v,
                "domain": ".tenders.co.il",
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            })
    return cookies


def load_jwt_token() -> str:
    """טוען JWT token מהקובץ."""
    token_file = os.path.join(DATA_DIR, "jwt_token.txt")
    if os.path.exists(token_file):
        with open(token_file) as f:
            t = f.read().strip()
        if t and len(t) > 50:
            return t
    return ""


def is_token_valid() -> bool:
    """בודק אם ה-JWT token עדיין תקף."""
    import requests as _req
    token = load_jwt_token()
    if not token:
        return False
    try:
        r = _req.get(
            "https://www.tenders.co.il/Data/api/Account/Me",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        return r.status_code == 200
    except Exception:
        return False


def auto_refresh_token() -> bool:
    """
    מתחבר אוטומטית ליפעת וחודש JWT token ללא התערבות משתמש.
    עובד רק אם אין OTP — כלומר אם האתר זוכר את המכשיר.
    """
    print("[TOKEN] Trying auto-refresh (headless)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            # טען עוגיות קיימות
            cookies = load_cookies()
            if cookies:
                context.add_cookies(cookies)

            page = context.new_page()
            captured = {"token": None}

            def on_response(response):
                if captured["token"]:
                    return
                try:
                    if "json" not in response.headers.get("content-type", ""):
                        return
                    body = response.text()
                    if '"Token"' in body or '"token"' in body:
                        import json as _j
                        data = _j.loads(body)
                        for k in ["Token", "token"]:
                            t = data.get(k, "")
                            if t and len(t) > 50 and t.startswith("eyJ"):
                                captured["token"] = t
                except Exception:
                    pass

            def on_request(request):
                if captured["token"]:
                    return
                auth = request.headers.get("authorization", "")
                if auth.lower().startswith("bearer "):
                    t = auth.split(" ", 1)[1].strip()
                    if t and len(t) > 50 and t.startswith("eyJ"):
                        captured["token"] = t

            page.on("response", on_response)
            page.on("request", on_request)

            # נסה לגשת לדף עם העוגיות הקיימות
            page.goto("https://www.tenders.co.il/home", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # אם לא נלכד, נסה כניסה אוטומטית
            if not captured["token"]:
                env_path = os.path.join(BASE_DIR, ".env")
                phone = password = ""
                if os.path.exists(env_path):
                    with open(env_path, encoding="utf-8-sig") as f:
                        for line in f:
                            if "TENDERS_PHONE=" in line:
                                phone = line.split("=", 1)[1].strip()
                            elif "TENDERS_PASSWORD=" in line:
                                password = line.split("=", 1)[1].strip()

                if phone and password:
                    login_link = page.query_selector('a:has-text("כניסה למנויים")')
                    if login_link:
                        login_link.click()
                        page.wait_for_timeout(1500)
                    user_f = page.query_selector('input[name="userName"]')
                    pass_f = page.query_selector('input[name="password"]')
                    if user_f and pass_f:
                        user_f.fill(phone)
                        pass_f.fill(password)
                        btn = page.query_selector('button:has-text("התחברות")')
                        if btn:
                            btn.click()
                            page.wait_for_timeout(3000)

            browser.close()

            if captured["token"]:
                token_file = os.path.join(DATA_DIR, "jwt_token.txt")
                with open(token_file, "w") as f:
                    f.write(captured["token"])
                print(f"[TOKEN] Auto-refresh OK! ({len(captured['token'])} chars)")
                return True
            else:
                print("[TOKEN] Auto-refresh failed — OTP required. Run refresh_token.py manually.")
                return False
    except Exception as e:
        print(f"[TOKEN] Auto-refresh error: {e}")
        return False


def make_context(playwright):
    """יוצר browser context עם קוקיות + JWT Bearer token."""
    browser = playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )

    # הכן headers — כולל Authorization אם יש JWT
    extra_headers = {"Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8"}
    token = load_jwt_token()
    if token:
        extra_headers["Authorization"] = f"Bearer {token}"

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="he-IL",
        viewport={"width": 1280, "height": 720},
        extra_http_headers=extra_headers
    )
    cookies = load_cookies()
    if cookies:
        context.add_cookies(cookies)
        print(f"Loaded {len(cookies)} cookies" + (" + JWT token" if token else " (no JWT)"))
    return browser, context


def scrape_tender_page(url: str) -> dict:
    """
    פותח דף מכרז ומחלץ את כל המידע.
    משלב: GetTender API (Summery, TenderLink) + scraping של אתר המפרסם.
    """
    with sync_playwright() as p:
        browser, context = make_context(p)
        page = context.new_page()
        tender_api_data = {}

        try:
            # לכוד GetTender API response
            def on_response(response):
                if "GetTender" in response.url:
                    try:
                        body = response.text()
                        if body and body.strip().startswith("{"):
                            tender_api_data["data"] = json.loads(body)
                    except Exception:
                        pass
            page.on("response", on_response)

            # אתחל Angular עם JWT
            page.goto("https://www.tenders.co.il/home", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(500)
            token = load_jwt_token()
            if token:
                page.evaluate(f"localStorage.setItem('token', '{token}');")

            # נווט למכרז — domcontentloaded מהיר יותר מ-networkidle שיכול לתקוע
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(5000)

            # טקסט בסיסי מהדף
            page_text = page.evaluate("() => document.body.innerText || ''")

            # נתח GetTender API data
            api = tender_api_data.get("data", {})
            summery = api.get("Summery", "") or ""
            tender_link = api.get("TenderLink", "") or ""
            tender_conditions = api.get("TenderConditions", "") or ""

            # אסוף מסמכים מה-API (TD=Tender Docs, AT=Attachments, GT=General Terms, VT, GRT)
            doc_fields = ["TD", "AT", "GT", "VT", "GRT"]
            api_docs = []
            for field in doc_fields:
                items = api.get(field, []) or []
                for item in items:
                    if isinstance(item, dict):
                        doc_url = item.get("Url") or item.get("url") or item.get("Path") or ""
                        doc_name = item.get("Name") or item.get("name") or item.get("Title") or field
                        if doc_url and doc_url.startswith("http"):
                            api_docs.append({"name": doc_name, "url": doc_url})

            # הרכב טקסט מלא: דף + summery + conditions
            full_text = page_text
            if summery and summery not in full_text:
                full_text += f"\n\nתיאור: {summery}"
            if tender_conditions and tender_conditions not in full_text:
                full_text += f"\n\nתנאי מכרז: {tender_conditions}"

            # נסה לסרוק אתר המפרסם לקבלת מסמכים
            external_docs = []
            external_text = ""
            if tender_link and len(external_docs) == 0:
                try:
                    ext_page = context.new_page()
                    ext_page.goto(tender_link, wait_until="domcontentloaded", timeout=12000)
                    ext_page.wait_for_timeout(1500)

                    ext_data = ext_page.evaluate("""() => {
                        const body = document.body.innerText || '';
                        const links = Array.from(document.querySelectorAll('a[href]'))
                            .filter(a => {
                                const h = a.href || '';
                                return h.match(/\\.(pdf|docx?|xlsx?|zip)$/i) ||
                                       h.includes('/docs/') || h.includes('/download') ||
                                       h.includes('/files/') || h.includes('/upload');
                            })
                            .map(a => ({
                                name: (a.innerText.trim() || a.href.split('/').pop()).substring(0, 100),
                                url: a.href
                            }))
                            .filter(d => d.url && d.url.startsWith('http'));
                        return {text: body.substring(0, 8000), links: links};
                    }""")
                    external_text = ext_data.get("text", "")
                    external_docs = ext_data.get("links", [])
                    if external_text:
                        full_text += f"\n\n=== מידע מאתר המפרסם ===\n{external_text[:5000]}"
                    ext_page.close()
                except Exception as ext_e:
                    pass  # external scrape failed — continue without

            all_docs = api_docs + external_docs
            # deduplicate
            seen_urls = set()
            unique_docs = []
            for d in all_docs:
                if d["url"] not in seen_urls:
                    seen_urls.add(d["url"])
                    unique_docs.append(d)

            return {
                "text": full_text[:25000],
                "documents": unique_docs,
                "tender_link": tender_link,
                "summery": summery,
                "url": url,
                "success": True,
            }
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {"text": "", "documents": [], "url": url, "success": False}
        finally:
            browser.close()


def get_feed_urls() -> list[str]:
    """שולף קישורי מכרזים מהפיד."""
    with sync_playwright() as p:
        browser, context = make_context(p)
        page = context.new_page()
        try:
            page.goto("https://www.tenders.co.il/main", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # גלול למטה לטעינת כל המכרזים
            for _ in range(8):
                page.evaluate("window.scrollBy(0, 900)")
                page.wait_for_timeout(600)

            urls = page.evaluate("""() => {
                return [...new Set(
                    Array.from(document.querySelectorAll('a[href*="/tender/"]'))
                    .map(a => a.href)
                    .filter(h => h.includes('tenders.co.il/tender/'))
                )];
            }""")
            print(f"Found {len(urls)} tender URLs in feed")
            return urls
        except Exception as e:
            print(f"Error getting feed: {e}")
            return []
        finally:
            browser.close()


def download_document(url: str, save_path: str) -> bool:
    """מוריד מסמך PDF/DOCX דרך Playwright."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    if os.path.exists(save_path):
        return True
    with sync_playwright() as p:
        browser, context = make_context(p)
        page = context.new_page()
        try:
            response = page.goto(url, timeout=30000)
            if response and response.ok:
                with open(save_path, "wb") as f:
                    f.write(response.body())
                return True
        except Exception as e:
            print(f"Download error {url}: {e}")
        finally:
            browser.close()
    return False


if __name__ == "__main__":
    print("בודק גישה ל-tenders.co.il...")
    urls = get_feed_urls()
    print(f"סה\"כ: {len(urls)} מכרזים")
    for u in urls[:5]:
        print(" -", u)
    if urls:
        print("\nפותח מכרז ראשון...")
        data = scrape_tender_page(urls[0])
        print(f"טקסט: {len(data['text'])} תווים")
        print(f"מסמכים: {len(data['documents'])}")
        print("100 תווים ראשונים:", data["text"][:100])

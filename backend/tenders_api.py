"""
קורא ישירות את ה-API של tenders.co.il.
משתמש ב-Playwright לטעינת הדף תחילה (לרענון cookies),
ואז קורא את ה-API מתוך הדפדפן עצמו.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from browser_scraper import load_cookies

BASE = "https://www.tenders.co.il"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def get_tender_ids_from_api(page_size: int = 50) -> list[dict]:
    """
    נכנס לאתר, מתחבר, וקורא את רשימת המכרזים מה-API.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        context.add_cookies(load_cookies())
        page = context.new_page()

        # 1. נכנס לדף הראשי לרענון session
        print("טוען דף ראשי...")
        page.goto(f"{BASE}/main", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        # 2. קורא ישירות את ה-API מתוך הדפדפן (עם ה-cookies הנוכחיים)
        print("קורא API...")
        api_result = page.evaluate(f"""async () => {{
            try {{
                const resp = await fetch('{BASE}/Data/api/Agent/GetAgentResults?page=1&pageSize={page_size}', {{
                    method: 'GET',
                    credentials: 'include',
                    headers: {{
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }}
                }});
                const status = resp.status;
                const text = await resp.text();
                return {{ status, text: text.substring(0, 10000) }};
            }} catch(e) {{
                return {{ error: e.toString() }};
            }}
        }}""")

        print(f"API Status: {api_result.get('status')}")
        text = api_result.get("text", "")

        if text:
            # שמור לקובץ
            with open(os.path.join(DATA_DIR, "agent_results.json"), "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Response size: {len(text)}")
            print(f"Preview: {text[:200]}")

            try:
                data = json.loads(text)
                if isinstance(data, list):
                    results = data
                    print(f"מכרזים: {len(results)}")
                elif isinstance(data, dict):
                    for key in ["results", "items", "tenders", "data", "Tenders"]:
                        if key in data and isinstance(data[key], list):
                            results = data[key]
                            break
                    print(f"Keys: {list(data.keys())[:10]}")
            except json.JSONDecodeError:
                print("Not JSON:", text[:100])

        browser.close()

    return results


def extract_tender_url(tender_data: dict) -> str:
    """מוצא URL מתוך נתוני מכרז."""
    # נסה שדות שונים
    for field in ["url", "Url", "URL", "link", "Link", "id", "Id", "ID", "TenderId"]:
        val = tender_data.get(field)
        if val:
            if str(val).startswith("http"):
                return val
            else:
                return f"{BASE}/tender/{val}"
    return ""


if __name__ == "__main__":
    tenders = get_tender_ids_from_api()
    print(f"\nסה\"כ: {len(tenders)} מכרזים")
    if tenders:
        print("שדות זמינים:", list(tenders[0].keys())[:15])
        for t in tenders[:3]:
            url = extract_tender_url(t)
            name = t.get("Name") or t.get("name") or t.get("Title") or t.get("title") or "?"
            print(f"  {name[:50]} → {url[:60]}")

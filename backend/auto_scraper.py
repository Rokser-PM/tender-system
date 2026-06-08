"""
מתחבר ל-Chrome הפתוח דרך CDP ושולף מכרזים חדשים מיפעת.
כך הוא רואה בדיוק מה שהמשתמש רואה - עם כל הסשן המלא.
"""
import urllib.request
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def find_running_chrome_port() -> int | None:
    """מוצא Chrome פתוח עם remote debugging."""
    for port in [9222, 9223, 9224, 9225]:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            return port
        except Exception:
            continue
    return None


def get_tenders_from_running_chrome() -> list[str]:
    """
    מתחבר ל-Chrome הפתוח ושולף קישורי מכרזים מהפיד של יפעת.
    """
    from playwright.sync_api import sync_playwright

    port = find_running_chrome_port()
    if not port:
        print("Chrome לא פתוח עם remote debugging.")
        print("פתח Chrome דרך הקיצור 'Chrome - Tender System' ונסה שוב.")
        return []

    print(f"מחובר ל-Chrome (port {port})...")
    urls = []

    with sync_playwright() as p:
        # מתחבר ל-Chrome הרץ — לא פותח Chrome חדש
        browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")

        # מוצא טאב של יפעת או פותח אחד
        context = browser.contexts[0]
        tenders_page = None

        for pg in context.pages:
            if "tenders.co.il" in pg.url:
                tenders_page = pg
                break

        if not tenders_page:
            tenders_page = context.new_page()

        # נווט לדף הראשי של יפעת
        print("נכנס לתenders.co.il/main...")
        tenders_page.goto("https://www.tenders.co.il/main",
                         wait_until="domcontentloaded", timeout=30000)

        # המתן לטעינת המכרזים
        tenders_page.wait_for_timeout(4000)

        # גלול למטה לטעינת כל המכרזים
        for _ in range(10):
            tenders_page.evaluate("window.scrollBy(0, 600)")
            tenders_page.wait_for_timeout(500)

        # שלוף את כל קישורי המכרזים
        urls = tenders_page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href*="/tender/"]'));
            return [...new Set(links.map(a => a.href).filter(h => h.includes('tenders.co.il/tender/')))];
        }""")

        page_text = tenders_page.inner_text("body")[:200]
        print(f"טקסט ראשון מהדף: {page_text[:100]}")
        print(f"נמצאו {len(urls)} מכרזים בפיד")

        # סגור את הטאב שפתחנו (אם פתחנו חדש)
        browser.close()

    return urls


def scrape_tender_via_chrome(url: str) -> dict | None:
    """
    פותח מכרז ספציפי ב-Chrome הקיים ושולף את הנתונים.
    """
    from playwright.sync_api import sync_playwright
    from main import parse_tender_text

    port = find_running_chrome_port()
    if not port:
        print("Chrome לא פתוח עם remote debugging.")
        return None

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")
        context = browser.contexts[0]
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            data = page.evaluate("""() => {
                const text = document.body.innerText || '';
                const docs = Array.from(document.querySelectorAll('a[href]'))
                    .filter(a => a.href.includes('/docs/') || a.href.match(/\\.(pdf|docx?|xlsx?)$/i))
                    .map(a => ({name: a.innerText.trim() || a.href.split('/').pop(), url: a.href}));
                return {text: text.substring(0, 20000), documents: docs};
            }""")

            result = parse_tender_text(url, data["text"], data["documents"])
            result["_full_text"] = data["text"]
            return result

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
        finally:
            page.close()
            browser.close()


if __name__ == "__main__":
    print("=== בדיקת חיבור ל-Chrome ===")
    port = find_running_chrome_port()
    if port:
        print(f"Chrome פתוח בפורט {port} ✓")
        urls = get_tenders_from_running_chrome()
        print(f"סה\"כ מכרזים: {len(urls)}")
        for u in urls[:5]:
            print(f"  {u}")
    else:
        print("Chrome לא פתוח. פתח דרך הקיצור 'Chrome - Tender System'")

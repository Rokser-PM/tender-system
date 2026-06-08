"""
קורא Gmail דרך Chrome שכבר פתוח (Chrome CDP).
לא צריך API Keys — מתחבר ל-Chrome הפתוח עם הלוגין הקיים.
"""
import re
import time
import os

TENDERS_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?tenders\.co\.il/tender/[\w\-_+/=%]+"
)

GMAIL_SEARCH = "from:tenders.co.il"


def find_chrome_cdp_port() -> int:
    """מוצא את ה-port של Chrome CDP."""
    import urllib.request
    for port in [9222, 9223, 9224]:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json", timeout=1)
            return port
        except Exception:
            continue
    return None


def get_gmail_page(playwright, port: int):
    """מחזיר דף Gmail מתוך Chrome הפתוח."""
    try:
        browser = playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
        for context in browser.contexts:
            for page in context.pages:
                if "mail.google.com" in page.url:
                    return browser, page
        # פתח Gmail בטאב חדש
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        page.goto("https://mail.google.com", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        return browser, page
    except Exception as e:
        raise Exception(f"לא ניתן להתחבר ל-Chrome. האם פתחת Chrome דרך הקיצור דרך? שגיאה: {e}")


def fetch_tender_urls_from_gmail() -> list[dict]:
    """
    מתחבר ל-Chrome הפתוח, מחפש מיילים מיפעת ומחלץ קישורי מכרזים.
    מחזיר רשימה של {subject, url}
    """
    from playwright.sync_api import sync_playwright

    port = find_chrome_cdp_port()
    if not port:
        print("Chrome לא פתוח עם remote debugging. פתח Chrome דרך הקיצור דרך 'Chrome - Tender System'")
        return []

    results = []
    print(f"מתחבר ל-Chrome בפורט {port}...")

    with sync_playwright() as p:
        browser, page = get_gmail_page(p, port)

        # חפש מיילים מיפעת
        print("מחפש מיילים מיפעת...")
        try:
            # נווט לחיפוש Gmail
            page.goto(
                f"https://mail.google.com/mail/u/0/#search/{GMAIL_SEARCH}",
                wait_until="domcontentloaded",
                timeout=20000
            )
            page.wait_for_timeout(3000)

            # מצא קישורי מכרזים בכל המיילים הגלויים
            email_rows = page.query_selector_all("tr.zA")
            print(f"נמצאו {len(email_rows)} מיילים")

            for row in email_rows[:20]:
                try:
                    # לחץ על המייל
                    subject_el = row.query_selector(".bog, .y6 span")
                    subject = subject_el.inner_text() if subject_el else "ללא נושא"
                    row.click()
                    page.wait_for_timeout(1500)

                    # חלץ קישורים
                    content = page.inner_text("body")
                    urls = list(set(TENDERS_URL_PATTERN.findall(content)))
                    for url in urls:
                        results.append({"subject": subject, "url": url})
                        print(f"  נמצא: {url[:60]}")

                    # חזור לרשימה
                    page.go_back(wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"  שגיאה במייל: {e}")
                    continue

        except Exception as e:
            print(f"שגיאת Gmail: {e}")

    return results


if __name__ == "__main__":
    urls = fetch_tender_urls_from_gmail()
    print(f"\nסה\"כ: {len(urls)} קישורי מכרזים")
    for u in urls:
        print(f"  {u['url']}")

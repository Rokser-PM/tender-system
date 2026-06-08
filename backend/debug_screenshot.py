import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from browser_scraper import load_cookies

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="he-IL"
    )
    context.add_cookies(load_cookies())
    page = context.new_page()
    page.goto("https://www.tenders.co.il/main", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    screenshot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "debug.png"))
    page.screenshot(path=screenshot_path)
    print(f"Screenshot: {screenshot_path}")

    # Check login status
    text = page.inner_text("body")[:500]
    print("Page text:", text[:300].encode('utf-8', errors='replace').decode('ascii', errors='replace'))

    links = page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a=>a.href).filter(h=>h.includes('/tender/'))")
    print(f"Tender links found: {len(links)}")
    for l in links[:5]: print(" -", l)

    browser.close()

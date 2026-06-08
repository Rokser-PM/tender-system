"""Debug - בדוק מה האתר מחזיר."""
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
    cookies = load_cookies()
    print(f"Cookies: {len(cookies)}")
    context.add_cookies(cookies)

    page = context.new_page()
    page.goto("https://www.tenders.co.il/main", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    url = page.url
    title = page.title()
    text = page.inner_text("body")[:300]
    all_links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)").count if hasattr(page, 'eval') else 0

    links = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a=>a.href).filter(h=>h.includes('/tender/')).slice(0,5)""")

    print(f"URL: {url}")
    print(f"Title: {title}")
    print(f"Text preview: {text[:200]}")
    print(f"Tender links: {links}")

    browser.close()

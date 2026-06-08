import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from browser_scraper import load_cookies

urls_to_try = [
    "https://www.tenders.co.il/tenders",
    "https://www.tenders.co.il/search",
    "https://www.tenders.co.il/main?all=1",
    "https://www.tenders.co.il/main?filter=all",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )
    context.add_cookies(load_cookies())
    page = context.new_page()

    # Try main page - click on search/filter to see all
    page.goto("https://www.tenders.co.il/main", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Save screenshot
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "data", "debug2.png"))

    # Try clicking on the search button to get all tenders
    try:
        page.click("button:has-text('חיפוש')", timeout=2000)
        page.wait_for_timeout(3000)
    except:
        pass

    # Try navigating to search with empty query
    page.goto("https://www.tenders.co.il/search?q=", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(os.path.dirname(__file__), "..", "data", "debug3.png"))

    links = page.evaluate("() => Array.from(document.querySelectorAll('a[href*=\"/tender/\"]')).map(a=>a.href)")
    print(f"Search page tender links: {len(links)}")
    for l in links[:5]:
        print(" -", l)

    browser.close()

print("Screenshots saved to data/debug2.png and data/debug3.png")

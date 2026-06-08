"""
מאזין לבקשות רשת של tenders.co.il כדי למצוא את ה-API שלהם.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright
from browser_scraper import load_cookies

api_calls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )
    context.add_cookies(load_cookies())

    # האזן לכל בקשות הרשת
    def on_request(request):
        url = request.url
        if "tenders.co.il" in url and any(x in url for x in ["/api/", "/v1/", "/v2/", "graphql", "tender", "search", "list"]):
            api_calls.append({
                "url": url,
                "method": request.method,
                "headers": dict(request.headers)
            })

    def on_response(response):
        url = response.url
        if "tenders.co.il" in url and any(x in url for x in ["/api/", "/v1/", "/v2/", "graphql"]):
            try:
                body = response.text()
                if len(body) > 100 and ('"tender' in body.lower() or '"id"' in body):
                    print(f"\n=== API FOUND ===")
                    print(f"URL: {url}")
                    print(f"Body preview: {body[:500]}")
                    with open(os.path.join(os.path.dirname(__file__), "..", "data", "api_response.json"), "w", encoding="utf-8") as f:
                        f.write(body[:10000])
            except Exception:
                pass

    context.on("request", on_request)
    context.on("response", on_response)

    page = context.new_page()
    print("טוען את הדף...")
    page.goto("https://www.tenders.co.il/main", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    print(f"\nסה\"כ API calls שנתפסו: {len(api_calls)}")
    for c in api_calls[:20]:
        print(f"  {c['method']} {c['url'][:100]}")

    browser.close()

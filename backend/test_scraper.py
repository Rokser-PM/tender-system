import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from scraper import get_chrome_cookies, make_session, get_main_feed_tenders

cookies = get_chrome_cookies()
print(f"Cookies found: {len(cookies)}")
if cookies:
    print("Cookie keys:", list(cookies.keys())[:8])

sess = make_session()
r = sess.get("https://www.tenders.co.il/main", timeout=15)
print(f"Status: {r.status_code}, size: {len(r.text)}")

# Check if logged in
logged_in = "tender_id" in r.text or len(r.text) > 10000
print(f"Got content: {logged_in}")

# Try to get tender URLs
urls = get_main_feed_tenders()
print(f"Tender URLs found: {len(urls)}")
for u in urls[:5]:
    print(" -", u)

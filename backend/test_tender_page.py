"""בדוק מה יש בדף מכרז אמיתי"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from browser_scraper import scrape_tender_page
from tenders_login import get_jwt_token
from doc_downloader import get_tender_docs_text, download_tender_doc, extract_text_from_file

# מכרז אמיתי מה-DB
TEST_URL = "https://www.tenders.co.il/tender/E0RoR7dceKDruV1C0a_SLA_kzwxEqualsXxEqualsX"

print("=== שלב 1: סריקת דף המכרז ===")
result = scrape_tender_page(TEST_URL)
print(f"הצלחה: {result['success']}")
print(f"טקסט: {len(result['text'])} תווים")
print(f"מסמכים שנמצאו: {len(result['documents'])}")
for d in result['documents']:
    print(f"  - {d['name']} -> {d['url']}")

print("\n=== שלב 2: הורדת מסמכים ===")
token = get_jwt_token()
for doc in result['documents'][:2]:
    url = doc['url']
    name = doc['name']
    ext = url.split('.')[-1] if '.' in url else 'pdf'
    filename = f"{name}.{ext}" if '.' not in name else name
    local = download_tender_doc(url, "test_tender", filename, token)
    if local:
        text = extract_text_from_file(local)
        print(f"  {name}: {len(text)} תווים")
        print(f"  תחילת המסמך: {text[:300]}")
    else:
        print(f"  {name}: נכשלה ההורדה")

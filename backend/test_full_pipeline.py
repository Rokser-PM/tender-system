"""בדיקה מלאה של ה-pipeline: scrape -> analyze -> save"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, upsert_tender, save_analysis, get_all_tenders
from browser_scraper import scrape_tender_page
from main import parse_tender_text
from analyzer import analyze_tender

TEST_URL = "https://www.tenders.co.il/tender/QdM4jh3DlUgpaEnnjsjYFQxEqualsXxEqualsX"

print("=== Step 1: Scraping tender page ===")
result = scrape_tender_page(TEST_URL)
print(f"Success: {result['success']}")
print(f"Text length: {len(result['text'])}")
print(f"Documents: {result['documents']}")
print(f"Text preview: {result['text'][:300]}")

print("\n=== Step 2: Parsing ===")
data = parse_tender_text(TEST_URL, result['text'], result['documents'])
print(f"Title: {data['title']}")
print(f"Publisher: {data['publisher']}")
print(f"Submission: {data['submission_date']}")
print(f"Branch: {data['branch']}")

print("\n=== Step 3: Analyzing with Claude ===")
if not os.environ.get("CLAUDE_API_KEY"):
    # Load from .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

analysis = analyze_tender(data)
print(f"Eligible: {analysis.get('eligible')}")
print(f"Reason: {analysis.get('eligibility_reason', '')[:100]}")
print(f"Conditions: {len(analysis.get('threshold_conditions', []))}")
print(f"Docs needed: {len(analysis.get('required_documents', []))}")
print(f"Questions: {len(analysis.get('questions_to_client', []))}")

print("\n=== Step 4: Saving to DB ===")
init_db()
upsert_tender(data)
save_analysis(data['tender_id'], analysis)
print("Saved!")

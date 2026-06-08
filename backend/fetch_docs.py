"""
שולף מסמכי מכרז ספציפי מדף האתר ומעדכן ה-DB.
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from database import get_conn


def fetch_and_update_documents(tender_id: str) -> list[dict]:
    """
    נכנס לדף המכרז בyifat, שולף קישורי מסמכים, ומעדכן ב-DB.
    """
    from browser_scraper import scrape_tender_page

    conn = get_conn()
    row = conn.execute("SELECT url FROM tenders WHERE tender_id=?", (tender_id,)).fetchone()
    conn.close()

    if not row:
        return []

    url = row["url"]
    result = scrape_tender_page(url)

    docs = result.get("documents", [])
    if docs:
        conn = get_conn()
        conn.execute(
            "UPDATE tenders SET documents=? WHERE tender_id=?",
            (json.dumps(docs, ensure_ascii=False), tender_id)
        )
        conn.commit()
        conn.close()
        print(f"Updated {len(docs)} documents for {tender_id}")

    return docs

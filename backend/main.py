"""
FastAPI backend — serves the dashboard data and triggers tender processing.
Run: python main.py
"""
import threading
import time
import json
import re
import os
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

from database import init_db, get_all_tenders, upsert_tender, save_analysis
try:
    from gmail_chrome import fetch_tender_urls_from_gmail as fetch_new_tender_urls
except Exception:
    from email_reader import fetch_new_tender_urls
from analyzer import analyze_tender

app = FastAPI(title="Tender System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def extract_tender_id(url: str) -> str:
    m = re.search(r"/tender/(.+)$", url)
    return m.group(1) if m else url.split("/")[-1]


def scrape_with_playwright(url: str) -> dict:
    """Use Playwright browser scraper."""
    try:
        from browser_scraper import scrape_tender_page
        result = scrape_tender_page(url)
        if result["success"] and result["text"]:
            return parse_tender_text(url, result["text"], result["documents"])
    except Exception as e:
        print(f"Playwright scrape error: {e}")
    return None


def parse_tender_text(url: str, text: str, documents: list) -> dict:
    """Parse tender text into structured data."""
    def find_field(label, t):
        m = re.search(rf"{re.escape(label)}[:\s]*(.+?)(?:\n|$)", t)
        return m.group(1).strip() if m else ""

    # Find title — skip navigation lines (contain |) and short lines
    title = ""
    for line in text.split("\n"):
        line = line.strip()
        if (len(line) > 15
                and "|" not in line
                and not any(x in line for x in ["התנתק", "מועדפים", "תזכורות", "פרסום", "חיפוש", "הגדרות"])
                and line.replace(" ", "") != ""):
            title = line
            break

    return {
        "tender_id": extract_tender_id(url),
        "url": url,
        "title": title,
        "publisher": find_field("שם המפרסם", text),
        "branch": find_field("ענפים", text),
        "tender_type": find_field("סוג מכרז", text),
        "submission_date": find_field("מועד ההגשה", text),
        "submission_notes": "",
        "description": text[500:1500] if len(text) > 500 else text,
        "raw_html": "",
        "documents": documents,
        "_full_text": text,
    }


def process_tender_url(url: str):
    """Scrape + analyze a single tender URL."""
    try:
        print(f"Processing: {url}")
        data = scrape_with_playwright(url)
        if not data:
            print(f"  → Failed to scrape {url}")
            return

        is_new = upsert_tender(data)
        if is_new:
            print(f"  [NEW] {data['title'][:60]}")
            analysis = analyze_tender(data)
            save_analysis(data["tender_id"], analysis)
            status = {1: "yes", 0: "no", -1: "unknown"}.get(analysis.get("eligible"), "?")
            print(f"  [ANALYSIS] eligible={status}")
        else:
            print(f"  [SKIP] Already in DB")
    except Exception as e:
        print(f"Error processing {url}: {e}")
        import traceback; traceback.print_exc()


def background_poll():
    """Poll tenders.co.il API every 15 minutes — fully automatic (no browser needed)."""
    while True:
        print("=== Scanning tenders.co.il API ===")
        try:
            from tenders_login import get_full_tender_list

            tender_list = get_full_tender_list()
            print(f"API returned {len(tender_list)} tenders")

            existing_ids = {t["tender_id"] for t in get_all_tenders()}
            new_count = 0

            for basic_data in tender_list:
                tid = basic_data.get("tender_id", "")
                if not tid or tid in existing_ids:
                    continue

                url = basic_data.get("url", "")
                if not url:
                    continue

                full_data = basic_data.copy()
                full_data["raw_html"] = ""
                full_data["_full_text"] = basic_data.get("description", "")

                is_new = upsert_tender(full_data)
                if is_new:
                    analysis = analyze_tender(full_data)
                    save_analysis(full_data["tender_id"], analysis)
                    new_count += 1
                    status = {1: "YES", 0: "NO", -1: "?"}.get(analysis.get("eligible"), "?")
                    print(f"  [NEW] eligible={status} | {full_data.get('title','')[:40]}")

                    # יצירת תיקייה ב-Google Drive אם עומד בתנאים
                    if analysis.get("eligible") == 1:
                        try:
                            from drive_manager import create_tender_folder
                            folder = create_tender_folder(full_data, analysis)
                            if folder:
                                print(f"  [DRIVE] Folder created")
                        except Exception as de:
                            print(f"  [DRIVE] Error: {de}")

            print(f"Done: {new_count} new tenders added")
        except Exception as e:
            print(f"Poll error: {e}")
            import traceback; traceback.print_exc()

        time.sleep(900)  # 15 minutes


@app.on_event("startup")
def startup():
    init_db()
    t = threading.Thread(target=background_poll, daemon=True)
    t.start()


# ── API Endpoints ──────────────────────────────────────────────

@app.get("/api/tenders")
def get_tenders():
    return JSONResponse(get_all_tenders())


@app.post("/api/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    """Manually trigger Gmail scan."""
    def scan():
        email_urls = fetch_new_tender_urls()
        for item in email_urls:
            process_tender_url(item["url"])
    background_tasks.add_task(scan)
    return {"status": "scan started"}


@app.post("/api/tender/process")
async def process_single(request: Request):
    """Process a specific tender URL (from user paste)."""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url or "tenders.co.il" not in url:
        return JSONResponse({"error": "קישור לא תקין"}, status_code=400)
    threading.Thread(target=process_tender_url, args=(url,), daemon=True).start()
    return {"status": "processing", "url": url}


@app.post("/api/tender/{tender_id}/status")
async def update_status(tender_id: str, request: Request):
    """עדכון סטטוס הגשה."""
    body = await request.json()
    status = body.get("status", "")
    from database import get_conn
    conn = get_conn()
    conn.execute("UPDATE tenders SET submission_status=? WHERE tender_id=?", (status, tender_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "submission_status": status}


@app.get("/api/tender/{tender_id}/fetch-docs")
def fetch_docs(tender_id: str):
    """שולף מסמכים לmכרז ספציפי."""
    def do_fetch():
        try:
            from fetch_docs import fetch_and_update_documents
            docs = fetch_and_update_documents(tender_id)
            print(f"[DOCS] {tender_id}: {len(docs)} docs fetched")
        except Exception as e:
            print(f"[DOCS] Error: {e}")
    threading.Thread(target=do_fetch, daemon=True).start()
    return {"status": "fetching"}


@app.get("/api/reanalyze-all-with-docs")
def reanalyze_all_with_docs(background_tasks: BackgroundTasks):
    """ניתוח מחדש של כל המכרזים עם eligible=-1."""
    def do_all():
        import json as _json
        import traceback
        import concurrent.futures
        from browser_scraper import scrape_tender_page, is_token_valid, auto_refresh_token
        from database import get_conn

        # בדוק טוקן לפני הניתוח
        if not is_token_valid():
            print("[TOKEN] Token expired — trying auto-refresh...")
            if not auto_refresh_token():
                print("[TOKEN] Auto-refresh failed. Analysis aborted.")
                return
        else:
            print("[TOKEN] Token OK.")

        tenders = get_all_tenders()
        # רק מכרזים שעדיין לא נותחו (eligible=-1 או None)
        pending = [t for t in tenders if t.get("eligible") in (-1, None)]
        print(f"Re-analyzing {len(pending)} pending tenders...")

        done = 0
        failed = 0
        for idx, t in enumerate(pending):
            # בדוק טוקן כל 10 מכרזים
            if idx > 0 and idx % 10 == 0:
                if not is_token_valid():
                    print("[TOKEN] Token expired mid-analysis — refreshing...")
                    auto_refresh_token()
            url = t.get("url", "")
            tid = t.get("tender_id", "?")
            if not url:
                continue
            try:
                # timeout לכל מכרז — 90 שניות מקסימום
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(scrape_tender_page, url)
                    try:
                        scraped = future.result(timeout=90)
                    except concurrent.futures.TimeoutError:
                        print(f"  [TIMEOUT] {tid} — דילוג")
                        failed += 1
                        continue

                if scraped.get("success"):
                    text = scraped.get("text", "")
                    docs = scraped.get("documents", [])
                    if docs:
                        conn = get_conn()
                        conn.execute("UPDATE tenders SET documents=? WHERE tender_id=?",
                                     (_json.dumps(docs, ensure_ascii=False), tid))
                        conn.commit()
                        conn.close()
                        t["documents"] = docs
                    if text:
                        t["_full_text"] = text
                    print(f"  [SCRAPED] {tid}: {len(docs)} docs, {len(text)} chars")

                analysis = analyze_tender(t)
                save_analysis(tid, analysis)
                status = {1: "YES", 0: "NO", -1: "?"}.get(analysis.get("eligible"), "?")
                done += 1
                print(f"  [{done}/{len(pending)}] {status} | {t.get('title','')[:45]}")

            except Exception as e:
                failed += 1
                print(f"  [ERROR] {tid}: {e}")
                traceback.print_exc()

        print(f"Re-analysis complete! done={done} failed={failed}")
    background_tasks.add_task(do_all)
    return {"status": "started", "message": "מנתח מחדש עם מסמכים — זה יקח כמה דקות"}


@app.get("/api/tender/{tender_id}/reanalyze")
def reanalyze(tender_id: str):
    """Re-run Claude analysis on an existing tender."""
    tenders = get_all_tenders()
    tender = next((t for t in tenders if t["tender_id"] == tender_id), None)
    if not tender:
        return JSONResponse({"error": "not found"}, status_code=404)
    threading.Thread(target=lambda: save_analysis(tender_id, analyze_tender(tender)), daemon=True).start()
    return {"status": "analyzing"}


# Serve frontend
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


try:
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
except Exception:
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

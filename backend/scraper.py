"""
Scrapes tender pages from tenders.co.il using session cookies from Chrome.
"""
import re
import json
import time
import requests
from bs4 import BeautifulSoup
import browser_cookie3
from config import DOCS_DIR, DATA_DIR
import os


def get_chrome_cookies() -> dict:
    """Extract tenders.co.il cookies — tries browser_cookie3 then falls back to manual file."""
    # 1. Try browser_cookie3 (works on older Chrome / Firefox)
    try:
        cookies = browser_cookie3.chrome(domain_name=".tenders.co.il")
        jar = {c.name: c.value for c in cookies}
        if jar:
            return jar
    except Exception:
        pass

    try:
        cookies = browser_cookie3.firefox(domain_name=".tenders.co.il")
        jar = {c.name: c.value for c in cookies}
        if jar:
            return jar
    except Exception:
        pass

    # 2. Fall back to manually saved cookies file
    cookie_file = os.path.join(DATA_DIR, "tenders_cookies.txt")
    if os.path.exists(cookie_file):
        jar = {}
        with open(cookie_file, encoding="utf-8-sig") as f:  # utf-8-sig strips BOM
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    # Skip cookies with non-latin1 characters (HTTP header limitation)
                    try:
                        k.encode("latin-1")
                        v.encode("latin-1")
                        jar[k] = v
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass
        if jar:
            print(f"Using manual cookies: {len(jar)} cookies")
            return jar

    print("No cookies found — scraping will not be authenticated")
    return {}


def make_session() -> requests.Session:
    sess = requests.Session()
    sess.cookies.update(get_chrome_cookies())
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
        "Referer": "https://www.tenders.co.il/main",
    })
    return sess


def extract_tender_id(url: str) -> str:
    """Extract the encoded tender ID from the URL."""
    match = re.search(r"/tender/(.+)$", url)
    return match.group(1) if match else url.split("/")[-1]


def scrape_tender(url: str) -> dict:
    """Scrape a single tender page and return structured data."""
    sess = make_session()
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    def text(sel):
        el = soup.select_one(sel)
        return el.get_text(strip=True) if el else ""

    # Extract all visible text paragraphs
    body_text = soup.get_text(separator="\n", strip=True)

    # Title
    title = ""
    for tag in ["h1", "h2", ".tender-title", "[class*='title']"]:
        el = soup.select_one(tag)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break

    # Extract structured fields from text
    def extract_field(label: str, text_block: str) -> str:
        pattern = rf"{re.escape(label)}[:\s]*(.+?)(?:\n|$)"
        m = re.search(pattern, text_block)
        return m.group(1).strip() if m else ""

    publisher = extract_field("שם המפרסם", body_text)
    submission_date = extract_field("מועד ההגשה", body_text)
    tender_type = extract_field("סוג מכרז", body_text)
    branch = extract_field("ענפים", body_text)

    # Extract submission notes (multi-line block)
    notes_match = re.search(r"הערות הגשה[:\s]*(.+?)(?:פרטים נוספים|ענפים|סיור קבלנים|$)",
                             body_text, re.DOTALL)
    submission_notes = notes_match.group(1).strip() if notes_match else ""

    # Extract description
    desc_match = re.search(r"פרטים\s*\n(.+?)(?:מסמכים מקושרים|$)", body_text, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract documents
    documents = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "tenders.co.il/docs" in href or any(ext in href for ext in [".pdf", ".docx", ".doc", ".xls", ".xlsx"]):
            documents.append({
                "name": a.get_text(strip=True) or os.path.basename(href),
                "url": href
            })

    tender_id = extract_tender_id(url)

    return {
        "tender_id": tender_id,
        "url": url,
        "title": title,
        "publisher": publisher,
        "branch": branch,
        "tender_type": tender_type,
        "submission_date": submission_date,
        "submission_notes": submission_notes,
        "description": description,
        "raw_html": resp.text[:50000],
        "documents": documents,
    }


def download_document(url: str, tender_id: str, filename: str) -> str:
    """Download a tender document. Returns local file path."""
    sess = make_session()
    safe_name = re.sub(r'[^\w\-_.]', '_', filename)
    safe_tid = re.sub(r'[^\w\-_]', '_', tender_id)
    folder = os.path.join(DOCS_DIR, safe_tid)
    os.makedirs(folder, exist_ok=True)
    local_path = os.path.join(folder, safe_name)

    if os.path.exists(local_path):
        return local_path

    resp = sess.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return local_path


def get_main_feed_tenders() -> list[str]:
    """Get all tender URLs from the main feed page."""
    sess = make_session()
    resp = sess.get("https://www.tenders.co.il/main", timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/tender/" in href and href not in urls:
            if not href.startswith("http"):
                href = "https://www.tenders.co.il" + href
            urls.append(href)
    return urls

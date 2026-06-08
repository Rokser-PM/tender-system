"""
מוריד מסמכי מכרז (PDF/DOCX) ישירות מ-tenders.co.il באמצעות JWT token.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
import requests

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "documents")


def download_tender_doc(url: str, tender_id: str, filename: str, token: str = None) -> str | None:
    """מוריד מסמך ומחזיר נתיב מקומי."""
    safe_tid = re.sub(r'[^\w\-_]', '_', str(tender_id))
    safe_name = re.sub(r'[^\w\-_.]', '_', filename)
    folder = os.path.join(DOCS_DIR, safe_tid)
    os.makedirs(folder, exist_ok=True)
    local_path = os.path.join(folder, safe_name)

    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        return local_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.tenders.co.il/",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        r = requests.get(url, headers=headers, timeout=30, stream=True)
        if r.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f"  Downloaded: {filename} ({os.path.getsize(local_path)//1024}KB)")
            return local_path
        else:
            print(f"  Download failed {r.status_code}: {url[:60]}")
            return None
    except Exception as e:
        print(f"  Download error: {e}")
        return None


def extract_text_from_file(file_path: str) -> str:
    """מחלץ טקסט מ-PDF או DOCX."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".docx":
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif ext == ".pdf":
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
    except Exception as e:
        print(f"  Text extraction error: {e}")
    return ""


def get_tender_docs_text(tender: dict, token: str = None) -> str:
    """
    מוריד ומחלץ טקסט מכל מסמכי המכרז.
    מחזיר טקסט מלא לניתוח Claude.
    """
    import json
    docs = tender.get("documents", [])
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except Exception:
            docs = []

    if not docs:
        return ""

    # מיין לפי עדיפות
    priority = ["חוברת", "מכרז", "תנאי", "קול קורא", "הזמנה", "נספח"]
    docs_sorted = sorted(docs, key=lambda d: next(
        (i for i, kw in enumerate(priority) if kw in d.get("name", "")), 99
    ))

    all_text = ""
    for doc in docs_sorted[:4]:  # עד 4 מסמכים
        url = doc.get("url", "")
        name = doc.get("name", "doc")
        if not url:
            continue

        ext = url.split(".")[-1].lower() if "." in url else "pdf"
        filename = f"{name}.{ext}" if "." not in name else name

        local = download_tender_doc(url, tender.get("tender_id", ""), filename, token)
        if local:
            text = extract_text_from_file(local)
            if text.strip():
                all_text += f"\n\n=== {name} ===\n{text[:15000]}"

    return all_text[:40000]

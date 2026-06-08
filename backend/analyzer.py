"""
Uses Claude API to analyze tender documents and check threshold conditions
against the company profile.
"""
import os
import json
import anthropic
import docx
import PyPDF2
from config import CLAUDE_API_KEY, CLAUDE_MODEL, COMPANY_PROFILE
try:
    from browser_scraper import download_document
except Exception:
    download_document = None


_client = None

def get_client():
    global _client
    if _client is None:
        if not CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY not set")
        _client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    return _client


def extract_text_from_file(file_path: str) -> str:
    """Extract text from docx or pdf."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == ".docx":
            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        elif ext == ".pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif ext in (".doc",):
            # fallback: read raw bytes, extract ascii text
            with open(file_path, "rb") as f:
                raw = f.read()
            text = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Could not extract {file_path}: {e}")
    return text[:40000]  # limit per document


def analyze_tender(tender: dict) -> dict:
    """
    Download tender documents, extract text, send to Claude.
    Returns structured analysis dict.
    """
    # Try to download full tender documents via Playwright (no login needed)
    try:
        from doc_downloader import get_tender_docs_text
        # Use cached token only — never trigger new login (prevents SMS)
        token = None
        token_file = os.path.join(os.path.dirname(__file__), "..", "data", "jwt_token.txt")
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.read().strip()
        downloaded_text = get_tender_docs_text(tender, token)
        if downloaded_text and len(downloaded_text) > 500:
            docs_text = downloaded_text
            print(f"  Using downloaded docs: {len(docs_text)} chars")
        else:
            docs_text = tender.get("_full_text", "")
    except Exception as e:
        docs_text = tender.get("_full_text", "")
        print(f"  Doc download skipped: {e}")

    # Also try to download and read document files
    if not docs_text or len(docs_text) < 500:
        documents = tender.get("documents", [])
        if isinstance(documents, str):
            try:
                documents = json.loads(documents)
            except Exception:
                documents = []

        priority_order = ["חוברת", "מכרז", "תנאי", "קול קורא", "הזמנה"]
        sorted_docs = sorted(documents, key=lambda d: next(
            (i for i, kw in enumerate(priority_order) if kw in d.get("name", "")), 99))

        for doc in sorted_docs[:3]:
            try:
                if download_document:
                    import re as _re2
                    import os as _os2
                    from config import DOCS_DIR
                    safe_name = _re2.sub(r'[^\w\-_.]', '_', doc["name"])
                    safe_tid = _re2.sub(r'[^\w\-_]', '_', tender["tender_id"])
                    folder = _os2.path.join(DOCS_DIR, safe_tid)
                    local_path = _os2.path.join(folder, safe_name)
                    if download_document(doc["url"], local_path):
                        text = extract_text_from_file(local_path)
                        if text.strip():
                            docs_text += f"\n\n=== {doc['name']} ===\n{text}"
            except Exception as e:
                print(f"Could not process doc {doc.get('name')}: {e}")

    # אם אין מסמכים — החזר -1 ישירות, אל תבזבז API call
    if not docs_text or len(docs_text.strip()) < 200:
        print(f"  [SKIP] No documents for {tender.get('tender_id','')} — returning unknown")
        return {
            "eligible": -1,
            "eligibility_reason": "לא הורדו מסמכי המכרז — לחץ 'נתח מחדש עם מסמכים'",
            "threshold_conditions": [],
            "required_documents": [],
            "questions_to_client": [],
            "submission_deadline": tender.get("submission_date", ""),
            "submission_fee": "לא צוין",
            "ai_summary": "ממתין לניתוח מסמכים"
        }

    # Build Claude prompt
    tender_context = f"""
שם מכרז: {tender.get('title', '')}
מפרסם: {tender.get('publisher', '')}
ענפים: {tender.get('branch', '')}
סוג מכרז: {tender.get('tender_type', '')}
מועד הגשה: {tender.get('submission_date', '')}
תיאור: {tender.get('description', '')[:500]}

תוכן מסמכי המכרז:
{docs_text[:30000]}
"""

    prompt = f"""אתה עוזר לחברת ניהול פרויקטים לבדוק האם היא יכולה להגיש הצעה למכרז.

פרופיל החברה:
{COMPANY_PROFILE}

פרטי המכרז:
{tender_context}

נתח את המכרז והחזר JSON בפורמט הבא בדיוק:
{{
  "eligible": 1,  // 1=כן, 0=לא, -1=לא ברור
  "eligibility_reason": "הסבר קצר למה כן/לא",
  "threshold_conditions": [
    {{
      "condition": "תיאור תנאי הסף",
      "met": true,  // האם החברה עומדת בתנאי
      "notes": "הסבר"
    }}
  ],
  "required_documents": [
    "מסמך 1",
    "מסמך 2"
  ],
  "questions_to_client": [
    "שאלה 1 שכדאי לשלוח למזמין",
    "שאלה 2"
  ],
  "submission_deadline": "DD/MM/YYYY HH:MM",
  "submission_fee": "סכום התשלום להגשה / רכישת מסמכים (לדוגמה: '500 ש\"ח', 'ללא תשלום', 'לא צוין')",
  "ai_summary": "סיכום קצר של המכרז ומהות העבודה"
}}

חשוב: החזר JSON בלבד, ללא הסברים נוספים."""

    try:
        msg = get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        # Clean up markdown code blocks if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}\nRaw: {raw[:500]}")
        return {
            "eligible": -1,
            "eligibility_reason": "שגיאה בניתוח",
            "threshold_conditions": [],
            "required_documents": [],
            "questions_to_client": [],
            "submission_deadline": tender.get("submission_date", ""),
            "ai_summary": "לא ניתן לנתח"
        }
    except Exception as e:
        print(f"Claude API error: {e}")
        return {
            "eligible": -1,
            "eligibility_reason": f"שגיאה: {str(e)}",
            "threshold_conditions": [],
            "required_documents": [],
            "questions_to_client": [],
            "submission_deadline": tender.get("submission_date", ""),
            "ai_summary": ""
        }

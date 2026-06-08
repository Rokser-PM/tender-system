import os

# Load .env file if present
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and "=" in _line and not _line.startswith("#"):
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# Claude API
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# Gmail / IMAP
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# tenders.co.il cookies (copied from browser)
TENDERS_COOKIES = {}  # populated at runtime from chrome session

# Paths — תומך ב-Render (DATA_DIR=/data) ובמקומי (../data)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "..", "data"))
DB_PATH = os.path.join(DATA_DIR, "tenders.db")
DOCS_DIR = os.path.join(DATA_DIR, "documents")

os.makedirs(DOCS_DIR, exist_ok=True)

# Company profile (loaded from docx extraction)
COMPANY_PROFILE = """
חברת רוכסר ניהול פרויקטים בע"מ
מייסד: אינג' עקיבא רוכסר — מהנדס מבנים B.Sc., בוגר הטכניון

שירותים: ניהול פרויקט, תיאום תכנון, פיקוח, לו"ז, תקציב, רישוי, ניהול מכרזים

ניסיון מוכח בפרויקטים:
- מגורים: אשטרום קרית יובל — 4 מגדלים 24 קומות, ~800 מ' ש"ח
- ציבורי/מוסדות: שירת האורן רמלה (בית אבות) — ~300 מ' ש"ח
- ציבורי/חינוך: מעונות סטודנטים — ~100 מ' ש"ח
- התחדשות עירונית פינוי ובינוי — ~70 מ' ש"ח
- ניהול מכרז פינוי בינוי פתח תקווה — ~60 מ' ש"ח
- תשתיות: חוות שרתים מנורה מערכות — ~50 מ' ש"ח
- ציבורי/בריאות: קופות חולים כללית ולאומית — ~8 מ' ש"ח
- התחדשות עירונית תמ"א 2 — ~20 מ' ש"ח
- ציבורי: שיפוץ בי"ס עירוני עיריית ת"א — ~25 מ' ש"ח

תחומי ניסיון: ניהול פרויקטים, פיקוח ובקרה, תיאום תכנון, ניהול מכרזים
סקטורים: מגורים, ציבורי, בריאות, חינוך, תשתיות, התחדשות עירונית
כישורים: מהנדס מבנים B.Sc. (טכניון)
"""

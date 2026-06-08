import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT UNIQUE,
            url TEXT,
            title TEXT,
            publisher TEXT,
            branch TEXT,
            tender_type TEXT,
            submission_date TEXT,
            submission_notes TEXT,
            description TEXT,
            raw_html TEXT,
            documents TEXT,  -- JSON list of {name, url}
            created_at TEXT DEFAULT (datetime('now')),
            analyzed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id TEXT REFERENCES tenders(tender_id),
            eligible INTEGER,  -- 1=yes, 0=no, -1=unknown
            eligibility_reason TEXT,
            threshold_conditions TEXT,  -- JSON list of conditions with status
            required_documents TEXT,    -- JSON list
            questions_to_client TEXT,   -- JSON list
            submission_deadline TEXT,
            ai_summary TEXT,
            analyzed_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_uid TEXT UNIQUE,
            subject TEXT,
            tender_url TEXT,
            processed_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def upsert_tender(data: dict) -> bool:
    """Insert or update tender. Returns True if new."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenders WHERE tender_id=?", (data["tender_id"],))
    exists = cur.fetchone()
    if exists:
        conn.close()
        return False
    row = {
        "tender_id": data.get("tender_id", ""),
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "publisher": data.get("publisher", ""),
        "branch": data.get("branch", ""),
        "tender_type": data.get("tender_type", ""),
        "submission_date": data.get("submission_date", ""),
        "submission_notes": data.get("submission_notes", ""),
        "description": data.get("description", ""),
        "raw_html": data.get("raw_html", ""),
        "documents": json.dumps(data.get("documents", [])),
    }
    cur.execute("""
        INSERT INTO tenders (tender_id, url, title, publisher, branch, tender_type,
            submission_date, submission_notes, description, raw_html, documents)
        VALUES (:tender_id, :url, :title, :publisher, :branch, :tender_type,
            :submission_date, :submission_notes, :description, :raw_html, :documents)
    """, row)
    conn.commit()
    conn.close()
    return True


def save_analysis(tender_id: str, analysis: dict):
    conn = get_conn()
    conn.execute("DELETE FROM analyses WHERE tender_id=?", (tender_id,))
    conn.execute("""
        INSERT INTO analyses (tender_id, eligible, eligibility_reason, threshold_conditions,
            required_documents, questions_to_client, submission_deadline, submission_fee, ai_summary)
        VALUES (:tender_id, :eligible, :eligibility_reason, :threshold_conditions,
            :required_documents, :questions_to_client, :submission_deadline, :submission_fee, :ai_summary)
    """, {
        "tender_id": tender_id,
        "eligible": analysis.get("eligible", -1),
        "eligibility_reason": analysis.get("eligibility_reason", ""),
        "threshold_conditions": json.dumps(analysis.get("threshold_conditions", []), ensure_ascii=False),
        "required_documents": json.dumps(analysis.get("required_documents", []), ensure_ascii=False),
        "questions_to_client": json.dumps(analysis.get("questions_to_client", []), ensure_ascii=False),
        "submission_deadline": analysis.get("submission_deadline", ""),
        "submission_fee": analysis.get("submission_fee", "לא צוין"),
        "ai_summary": analysis.get("ai_summary", ""),
    })
    conn.execute("UPDATE tenders SET analyzed_at=datetime('now') WHERE tender_id=?", (tender_id,))
    conn.commit()
    conn.close()


def get_all_tenders():
    conn = get_conn()
    rows = conn.execute("""
        SELECT t.*, t.submission_status, a.eligible, a.eligibility_reason, a.threshold_conditions,
               a.required_documents, a.questions_to_client, a.submission_deadline as ai_deadline,
               a.submission_fee, a.ai_summary
        FROM tenders t
        LEFT JOIN analyses a ON t.tender_id = a.tender_id
        ORDER BY t.created_at DESC
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        for field in ["documents", "threshold_conditions", "required_documents", "questions_to_client"]:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        result.append(d)
    return result


def log_email(uid: str, subject: str, url: str):
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO email_log (email_uid, subject, tender_url) VALUES (?,?,?)",
                     (uid, subject, url))
        conn.commit()
    except Exception:
        pass
    conn.close()


def is_email_processed(uid: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT id FROM email_log WHERE email_uid=?", (uid,)).fetchone()
    conn.close()
    return row is not None

"""
Reads Gmail via IMAP using an App Password.
Finds emails from tenders.co.il / יפעת and extracts tender URLs.
"""
import imaplib
import email
import re
from email.header import decode_header
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
from database import log_email, is_email_processed


TENDERS_URL_PATTERN = re.compile(r"https?://(?:www\.)?tenders\.co\.il/tender/[\w\-_+/=]+")


def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result


def get_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return body


def fetch_new_tender_urls() -> list[dict]:
    """Connect to Gmail and return list of {uid, subject, url} for new tenders."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Gmail credentials not configured. Skipping email check.")
        return []

    results = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for emails from tenders.co.il
        _, uids = mail.search(None, '(OR FROM "tenders.co.il" FROM "yifat")')
        uid_list = uids[0].split() if uids[0] else []

        for uid in uid_list[-50:]:  # last 50 emails
            uid_str = uid.decode()
            if is_email_processed(uid_str):
                continue

            _, data = mail.fetch(uid, "(RFC822)")
            if not data or not data[0]:
                continue

            msg = email.message_from_bytes(data[0][1])
            subject = decode_str(msg.get("Subject", ""))
            body = get_body(msg)
            full_text = subject + " " + body

            urls = TENDERS_URL_PATTERN.findall(full_text)
            for url in set(urls):
                log_email(uid_str, subject, url)
                results.append({"uid": uid_str, "subject": subject, "url": url})

        mail.logout()
    except Exception as e:
        print(f"Email error: {e}")

    return results

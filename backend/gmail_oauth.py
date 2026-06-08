"""
Gmail OAuth2 reader — works with Google Workspace accounts.
First run: opens browser for authorization.
After that: fully automatic, token auto-refreshes.
"""
import os
import json
import re
import base64
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "gmail_token.json")
CREDS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "gmail_credentials.json")

TENDERS_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?tenders\.co\.il/tender/[\w\-_+/=%]+"
)


def get_gmail_service():
    """Get authenticated Gmail service. Opens browser on first run."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(
                    f"credentials.json לא נמצא. הורד אותו מ-Google Cloud Console ושמור ב:\n{CREDS_FILE}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("Gmail token saved — לא צריך לאשר שוב בעתיד")

    service = build("gmail", "v1", credentials=creds)
    return service


def get_message_text(service, msg_id: str) -> str:
    """Extract plain text from a Gmail message."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})

    def extract_parts(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        text = ""
        if mime in ("text/plain", "text/html") and data:
            text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for sub in part.get("parts", []):
            text += extract_parts(sub)
        return text

    return extract_parts(payload)


def fetch_new_tender_urls() -> list[dict]:
    """
    Scan Gmail for emails from tenders.co.il and return new tender URLs.
    Returns list of {uid, subject, url}
    """
    try:
        from database import log_email, is_email_processed
    except ImportError:
        log_email = lambda *a: None
        is_email_processed = lambda x: False

    results = []
    try:
        service = get_gmail_service()

        # Search for emails from tenders.co.il
        query = 'from:tenders.co.il OR from:yifat newer_than:7d'
        response = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()

        messages = response.get("messages", [])
        print(f"Found {len(messages)} emails from tenders.co.il")

        for msg in messages:
            msg_id = msg["id"]
            if is_email_processed(msg_id):
                continue

            # Get subject
            meta = service.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["Subject"]
            ).execute()
            subject = next(
                (h["value"] for h in meta.get("payload", {}).get("headers", [])
                 if h["name"] == "Subject"), ""
            )

            # Get full text and find tender URLs
            text = get_message_text(service, msg_id)
            urls = list(set(TENDERS_URL_PATTERN.findall(text)))

            for url in urls:
                log_email(msg_id, subject, url)
                results.append({"uid": msg_id, "subject": subject, "url": url})
                print(f"  Found tender URL: {url[:60]}")

    except Exception as e:
        print(f"Gmail error: {e}")

    return results


if __name__ == "__main__":
    print("Testing Gmail connection...")
    urls = fetch_new_tender_urls()
    print(f"\nTotal tender URLs found: {len(urls)}")
    for u in urls:
        print(f"  [{u['subject'][:40]}] {u['url'][:60]}")

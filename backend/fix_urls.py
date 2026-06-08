"""תקן את ה-URLs של מכרזים שנשמרו עם ID מספרי."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from tenders_login import login_and_get_token, make_api_session, BASE
from database import get_conn

token = login_and_get_token()
sess = make_api_session(token)

# שלוף את כל המכרזים מה-API עם EncID
all_tenders = []
for page in range(1, 10):
    r = sess.get(f"{BASE}/Data/api/Agent/GetAgentResults?page={page}&pageSize=50", timeout=15)
    if r.status_code != 200:
        break
    data = r.json()
    items = data.get("data", [])
    if not items:
        break
    all_tenders.extend(items)
    if len(items) < 50:
        break

print(f"Fetched {len(all_tenders)} tenders from API")

# צור מילון TenderID → EncID
id_to_enc = {}
for t in all_tenders:
    tid = str(t.get("TenderID", ""))
    enc = t.get("EncID", "")
    if tid and enc:
        id_to_enc[tid] = enc

print(f"ID-EncID map: {len(id_to_enc)} entries")

# עדכן ב-DB
conn = get_conn()
rows = conn.execute("SELECT tender_id, url FROM tenders").fetchall()
updated = 0
for row in rows:
    tid = row["tender_id"]
    url = row["url"] or ""
    # אם ה-URL הוא /tender/[מספר] — תקן אותו
    if f"/tender/{tid}" in url and tid in id_to_enc:
        new_url = f"{BASE}/tender/{id_to_enc[tid]}"
        conn.execute("UPDATE tenders SET url=? WHERE tender_id=?", (new_url, tid))
        updated += 1
        print(f"  Fixed: {tid} -> {new_url[:60]}")

conn.commit()
conn.close()
print(f"\nFixed {updated} URLs")

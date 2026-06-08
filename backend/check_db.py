import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_all_tenders
tenders = get_all_tenders()
print(f"Total tenders in DB: {len(tenders)}")
for t in tenders:
    title = (t.get("title") or "").encode("ascii", errors="replace").decode()[:40]
    elig = t.get("eligible")
    tid = str(t.get("tender_id", ""))[:20]
    print(f"  [{elig}] {tid} | {title}")

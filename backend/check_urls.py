import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from database import get_all_tenders

tenders = get_all_tenders()
print(f"Total: {len(tenders)}")
for t in tenders[:8]:
    docs = t.get("documents") or []
    if isinstance(docs, str):
        try: docs = json.loads(docs)
        except: docs = []
    tid = str(t.get("tender_id",""))[:15]
    url = str(t.get("url",""))[:60]
    ndocs = len(docs)
    print(f"  [{tid}] url={url} docs={ndocs}")
    if docs:
        for d in docs[:2]:
            print(f"    doc: {d.get('name','')} -> {str(d.get('url',''))[:50]}")

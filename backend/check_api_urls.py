"""בדוק את שדות ה-URL בתשובת ה-API"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from tenders_login import login_and_get_token, make_api_session

BASE = "https://www.tenders.co.il"
token = login_and_get_token()
sess = make_api_session(token)

r = sess.get(f"{BASE}/Data/api/Agent/GetAgentResults?page=1&pageSize=3", timeout=15)
data = r.json()
items = data.get("data", [])

print(f"Total fields in first item:")
if items:
    first = items[0]
    for k, v in first.items():
        print(f"  {k}: {str(v)[:80]}")

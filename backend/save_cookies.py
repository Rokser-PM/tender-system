"""
הרץ סקריפט זה פעם אחת כדי לשמור את הקוקיות מ-Chrome.
הוראות:
1. פתח Chrome עם tenders.co.il מחובר
2. פתח DevTools (F12) -> Console
3. הדבק את הפקודה הבאה ב-Console:
   copy(document.cookie)
4. הדבק את הפלט כאן
"""
import os, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
COOKIE_FILE = os.path.join(DATA_DIR, "tenders_cookies.txt")

print("=" * 50)
print("שמירת קוקיות מ-Chrome")
print("=" * 50)
print()
print("1. פתח Chrome עם tenders.co.il (מחובר)")
print("2. לחץ F12 (DevTools) -> Console")
print("3. הדבק והרץ: copy(document.cookie)")
print("4. לחץ Enter כאן והדבק את הקוקיות:")
print()

cookie_str = input("> ").strip()

if not cookie_str:
    print("לא הוכנס כלום")
    sys.exit(1)

# Parse cookies string (key=val; key2=val2; ...)
cookies = {}
for part in cookie_str.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()

os.makedirs(DATA_DIR, exist_ok=True)
with open(COOKIE_FILE, "w") as f:
    for k, v in cookies.items():
        f.write(f"{k}={v}\n")

print(f"\nנשמרו {len(cookies)} קוקיות ב-{COOKIE_FILE}")
print("עכשיו המערכת יכולה לגשת ל-tenders.co.il!")

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, upsert_tender, save_analysis

init_db()

tenders = [
    {
        "tender_id": "E0RoR7dceKDruV1C0a",
        "url": "https://www.tenders.co.il/tender/E0RoR7dceKDruV1C0a_SLA_kzwxEqualsXxEqualsX",
        "title": "ניהול הליך הסדרת שטחי מקרקעין במזרח ירושלים ובאיו\"ש",
        "publisher": "משרד המשפטים",
        "branch": "שירותים משפטיים, תכנון יעוץ אדריכלי, מיפוי ומדידה",
        "tender_type": "פומבי/כללי",
        "submission_date": "17/06/2026 12:00",
        "submission_notes": "הגשה מקוונת דרך מערכת יהלום",
        "description": "ניהול ותיאום הליכי הסדר ורישום זכויות במקרקעין",
        "raw_html": "",
        "documents": [
            {"name": "חוברת המכרז", "url": "https://www.tenders.co.il/docs/2026/05/28/1986180.docx"},
            {"name": "מודעה לעיתונות", "url": "https://www.tenders.co.il/docs/2026/05/28/1986181.pdf"}
        ]
    },
    {
        "tender_id": "QdM4jh3DlUgpaEnnj",
        "url": "https://www.tenders.co.il/tender/QdM4jh3DlUgpaEnnjsjYFQxEqualsXxEqualsX",
        "title": "הזמנה להציע הצעות להקמת פרויקט התחדשות עירונית — פינוי בינוי, מעפילי אגוז תל אביב",
        "publisher": "עו\"ד יעקב אמסטר",
        "branch": "בנייה ופיתוח, קבלנות, התחדשות עירונית",
        "tender_type": "כונס נכסים",
        "submission_date": "30/07/2026 17:00",
        "submission_notes": "הגשה ידנית למשרד עורך הדין",
        "description": "הקמת פרויקט התחדשות עירונית במסלול פינוי בינוי",
        "raw_html": "",
        "documents": [
            {"name": "חוברת ההזמנה", "url": "https://www.tenders.co.il/tender/QdM4jh3DlUgpaEnnjsjYFQxEqualsXxEqualsX"}
        ]
    },
    {
        "tender_id": "Y847taSA4oayYs3ku",
        "url": "https://www.tenders.co.il/tender/Y847taSA4o_SLA_ayYs3kuZWXQxEqualsXxEqualsX",
        "title": "העסקת יועצים/מתכננים פרויקט קצירונים",
        "publisher": "המשרד לביטחון פנים — שירות בתי הסוהר",
        "branch": "תכנון, יעוץ, הנדסה",
        "tender_type": "פטור ממכרז",
        "submission_date": "",
        "submission_notes": "",
        "description": "העסקת יועצים ומתכננים לפרויקט קצירונים",
        "raw_html": "",
        "documents": []
    }
]

analyses = [
    {
        "tender_id": "E0RoR7dceKDruV1C0a",
        "eligible": 0,
        "eligibility_reason": "המכרז דורש ניסיון ספציפי בהסדרת מקרקעין ורישיון מודד — אינו בליבת הפעילות של החברה.",
        "threshold_conditions": [
            {"condition": "ניסיון בהסדרת מקרקעין", "met": False, "notes": "לחברה אין ניסיון ספציפי בתחום זה"},
            {"condition": "רישיון מודד מוסמך", "met": False, "notes": "נדרש רישיון מדידה"},
            {"condition": "ניסיון בעבודה מול רשויות", "met": True, "notes": "ניסיון מוכח מול עירייה ומשרדי ממשלה"}
        ],
        "required_documents": ["תצהיר ניסיון", "רישיון מודד", "אישור עוסק מורשה"],
        "questions_to_client": [],
        "submission_deadline": "17/06/2026 12:00",
        "ai_summary": "מכרז לניהול הליכי הסדרת מקרקעין — אינו מתאים לחברת ניהול פרויקטים ללא רישיון מדידה"
    },
    {
        "tender_id": "QdM4jh3DlUgpaEnnj",
        "eligible": 1,
        "eligibility_reason": "החברה עומדת בתנאי הסף — ניסיון מוכח בפרויקטי פינוי בינוי ובניהול מכרזים מורכבים.",
        "threshold_conditions": [
            {"condition": "ניסיון בפרויקטי פינוי בינוי", "met": True, "notes": "ניסיון בפינוי בינוי בהיקף 70-60 מ' ש\"ח"},
            {"condition": "ניהול פרויקטים בהיקף 30+ מ' ש\"ח", "met": True, "notes": "פרויקטים עד 800 מ' ש\"ח"},
            {"condition": "מהנדס/הנדסאי מוסמך", "met": True, "notes": "מייסד — מהנדס מבנים B.Sc. טכניון"},
            {"condition": "ניסיון בהתחדשות עירונית", "met": True, "notes": "ניסיון מוכח בתמ\"א 2 ופינוי בינוי"}
        ],
        "required_documents": ["חוברת ההצעה", "תצהיר ניסיון", "CV מנהל הפרויקט", "רשימת פרויקטים דומים", "אישור עו\"ד"],
        "questions_to_client": [
            "מהו לוח הזמנים הצפוי לפרויקט ומתי מתוכנן לתחילת ביצוע?",
            "האם ישנה חברה יזמית שכבר נבחרה?",
            "מהם קריטריוני ההמלצה על קבלן ביצוע?"
        ],
        "submission_deadline": "30/07/2026 17:00",
        "ai_summary": "מכרז להקמת פרויקט פינוי בינוי בתל אביב — מתאים מאוד לחברה. ניסיון מוכח בדיוק בתחום זה."
    },
    {
        "tender_id": "Y847taSA4oayYs3ku",
        "eligible": -1,
        "eligibility_reason": "ממתין לניתוח — נדרש Claude API Key",
        "threshold_conditions": [],
        "required_documents": [],
        "questions_to_client": [],
        "submission_deadline": "",
        "ai_summary": ""
    }
]

for t in tenders:
    upsert_tender(t)
for a in analyses:
    save_analysis(a["tender_id"], a)

print("Demo data loaded — 3 tenders saved to DB")

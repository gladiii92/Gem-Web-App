# recategorize.py — einmalig
import json
from categorizer import categorize

with open("crawl_db.json", "r", encoding="utf-8") as f:
    db = json.load(f)

db = [categorize(e) for e in db]

with open("crawl_db.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"✅ {len(db)} Einträge rekategorisiert")
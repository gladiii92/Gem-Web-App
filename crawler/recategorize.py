"""
recategorize.py — wendet categorizer.py rückwirkend auf crawl_db.json an
Überschreibt category + category_id für alle Einträge neu.
crawl_db.json wird in-place aktualisiert, Rohdaten bleiben erhalten.
"""

import json
from pathlib import Path
from categorizer import categorize

CRAWL_DB = Path(__file__).parent / "crawl_db.json"

with open(CRAWL_DB, "r", encoding="utf-8") as f:
    db = json.load(f)

before = {}
after  = {}

for e in db:
    old_cat = e.get("category", "unknown")
    before[old_cat] = before.get(old_cat, 0) + 1
    categorize(e)
    new_cat = e.get("category", "unknown")
    after[new_cat] = after.get(new_cat, 0) + 1

with open(CRAWL_DB, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# ── Report
print(f"\n✅ Re-Kategorisierung abgeschlossen — {len(db)} Einträge")

print("\n--- Vorher (Top 15) ---")
for cat, n in sorted(before.items(), key=lambda x: -x[1])[:15]:
    print(f"  {n:>4}x  {cat}")

print("\n--- Nachher (Top 15) ---")
for cat, n in sorted(after.items(), key=lambda x: -x[1])[:15]:
    print(f"  {n:>4}x  {cat}")

print("\n--- Neu erkannte Kategorien (vorher unknown*) ---")
new_cats = [c for c in after if not c.startswith("unknown") and before.get(c, 0) == 0]
for cat in sorted(new_cats):
    print(f"  {after[cat]:>4}x  {cat}")
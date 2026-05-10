
import json
from collections import Counter

with open("crawl_db.json", "r", encoding="utf-8") as f:
    db = json.load(f)

unknowns = [e for e in db if e.get("category") == "unknown"]

# gem_category zählen — welche Steintypen sind betroffen?
gem_cats = Counter(e.get("gem_category", "?") for e in unknowns)
print("=== Unknown nach gem_category ===")
for cat, count in gem_cats.most_common(20):
    print(f"  {count:4d}x  {cat}")

# 5 Beispiel-Titel pro Kategorie ausgeben
print("\n=== Beispiel-Titel (erste 3 pro Kategorie) ===")
seen = {}
for e in unknowns:
    cat = e.get("gem_category", "?")
    if cat not in seen:
        seen[cat] = []
    if len(seen[cat]) < 3:
        seen[cat].append(e["name_raw"])

for cat, titles in list(seen.items())[:15]:
    print(f"\n  [{cat}]")
    for t in titles:
        print(f"    - {t}")

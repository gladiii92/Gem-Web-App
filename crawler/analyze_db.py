
import json
from collections import Counter

with open("gems.db", "r", encoding="utf-8") as f:
    db = json.load(f)

print(f"=== crawl_db.json Analyse ===")
print(f"Gesamt: {len(db)} Einträge")

sources = Counter(e["source"] for e in db)
print(f"\nNach Quelle: {dict(sources)}")

price_types = Counter(e["price_type"] for e in db)
print(f"Preistyp: {dict(price_types)}")

categories = Counter(e.get("category", "?") for e in db)
print(f"\nTop 10 Kategorien:")
for cat, count in categories.most_common(10):
    print(f"  {count:4d}x  {cat}")

unknown = sum(1 for e in db if e.get("category") == "unknown")
print(f"\nUnbekannte Kategorie: {unknown} ({unknown/len(db)*100:.1f}%)")

treatments = Counter(e.get("treatment", "?") for e in db)
print(f"\nBehandlung: {dict(treatments)}")

prices = [e["price_usd"] for e in db if e.get("price_usd")]
if prices:
    print(f"\nPreis-Range: ${min(prices):.0f} – ${max(prices):.0f}")
    print(f"Median Preis: ${sorted(prices)[len(prices)//2]:.0f}")

has_image = sum(1 for e in db if e.get("image_url"))
print(f"\nMit Bild-URL: {has_image}/{len(db)} ({has_image/len(db)*100:.1f}%)")

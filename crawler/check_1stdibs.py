import json, statistics

db   = json.load(open("crawl_db.json", encoding="utf-8"))
dibs = [e for e in db if e["source"] == "1stdibs"]

print(f"1stDibs Eintraege : {len(dibs)}")
print(f"Mit Preis         : {len([e for e in dibs if e.get('price_usd')])}")
print(f"Mit Gewicht       : {len([e for e in dibs if e.get('carat')])}")
print(f"Mit Clarity       : {len([e for e in dibs if e.get('clarity')])}")
print(f"Mit Origin        : {len([e for e in dibs if e.get('origin')])}")
print(f"Mit Kategorie     : {len([e for e in dibs if e.get('category')])}")

prices = sorted([e["price_usd"] for e in dibs if e.get("price_usd")])
print(f"\nPreis Min   : ${min(prices):>10,.0f}")
print(f"Preis Median: ${statistics.median(prices):>10,.0f}")
print(f"Preis Max   : ${max(prices):>10,.0f}")

# Fake-Preis Check — wie viele haben exakt $1000?
fake = [e for e in dibs if e.get("price_usd") == 1000.0]
print(f"\nExakt $1,000 (Verdacht Placeholder): {len(fake)}/{len(dibs)}")

# Preisverteilung
buckets = {"<$500": 0, "$500-2k": 0, "$2k-10k": 0, ">$10k": 0}
for e in dibs:
    p = e.get("price_usd", 0)
    if p < 500:       buckets["<$500"] += 1
    elif p < 2000:    buckets["$500-2k"] += 1
    elif p < 10000:   buckets["$2k-10k"] += 1
    else:             buckets[">$10k"] += 1
print("\nPreisverteilung:")
for k, v in buckets.items():
    print(f"  {k:>12}: {v:>4} ({v/len(dibs)*100:.0f}%)")

print("\n--- Beispiel (hoher Preis) ---")
top = max(dibs, key=lambda e: e.get("price_usd", 0))
print(json.dumps(top, indent=2, ensure_ascii=False))
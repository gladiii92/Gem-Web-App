import json

db = json.load(open('crawl_db.json', encoding='utf-8'))
alex = [e for e in db if 'Alexandrit' in e.get('category', '')]
alex.sort(key=lambda x: x.get('price_usd', 0))

print(f"{'Preis':>10}  {'Typ':>10}  {'Karat':>6}  Titel")
print("-" * 80)
for e in alex:
    print(f"${e.get('price_usd', 0):>9,.0f}  {e.get('price_type','?'):>10}  {str(e.get('carat','?')):>6}  {e.get('name_raw','')[:50]}")

print(f"\nGesamt: {len(alex)} Alexandrite")
import sqlite3

conn = sqlite3.connect("crawler/gems.db")
cur = conn.cursor()

cur.execute("""
    SELECT category, carat, price_usd, price_type, source
    FROM crawl_entries
    WHERE clarity = 'SI2'
    ORDER BY price_usd DESC
""")

rows = cur.fetchall()
print(f"SI2 Eintraege gesamt: {len(rows)}")
print()
print(f"{'Kategorie':<45} {'Karat':>6} {'Preis USD':>12} {'Typ':<10} {'Quelle'}")
print("-" * 90)
for r in rows:
    cat = (r[0] or "unknown")[:44]
    print(f"{cat:<45} {r[1]:>6.2f} {r[2]:>12.2f} {r[3]:<10} {r[4]}")

conn.close()
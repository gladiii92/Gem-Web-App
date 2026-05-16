import sqlite3
from collections import Counter

conn = sqlite3.connect("gems.db")
cur = conn.cursor()

# Tabellen anzeigen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"=== gems.db Analyse ===")
print(f"Tabellen: {tables}")

# Haupttabelle automatisch erkennen
main_table = tables[0] if tables else None
if not main_table:
    print("Keine Tabellen gefunden!")
    conn.close()
    exit()

# Spalten anzeigen
cur.execute(f"PRAGMA table_info({main_table})")
cols = [r[1] for r in cur.fetchall()]
print(f"\nSpalten in '{main_table}': {cols}")

# Gesamtanzahl
cur.execute(f"SELECT COUNT(*) FROM {main_table}")
total = cur.fetchone()[0]
print(f"\nGesamt: {total} Einträge")

# Nach Quelle
if "source" in cols:
    cur.execute(f"SELECT source, COUNT(*) FROM {main_table} GROUP BY source ORDER BY COUNT(*) DESC")
    print(f"\nNach Quelle:")
    for row in cur.fetchall():
        print(f"  {row[1]:5d}x  {row[0]}")

# Nach Kategorie (Top 10)
if "category" in cols:
    cur.execute(f"SELECT category, COUNT(*) FROM {main_table} GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
    print(f"\nTop 10 Kategorien:")
    for row in cur.fetchall():
        print(f"  {row[1]:5d}x  {row[0]}")

# Unbekannte Kategorien
if "category" in cols:
    cur.execute(f"SELECT COUNT(*) FROM {main_table} WHERE category = 'unknown' OR category IS NULL")
    unknown = cur.fetchone()[0]
    print(f"\nUnbekannte Kategorie: {unknown} ({unknown/total*100:.1f}%)")

# Preisrange
if "price_usd" in cols:
    cur.execute(f"SELECT MIN(price_usd), MAX(price_usd) FROM {main_table} WHERE price_usd IS NOT NULL")
    row = cur.fetchone()
    print(f"\nPreis-Range: ${row[0]:.0f} – ${row[1]:.0f}")

# Mit Bild
if "image_url" in cols:
    cur.execute(f"SELECT COUNT(*) FROM {main_table} WHERE image_url IS NOT NULL AND image_url != ''")
    has_img = cur.fetchone()[0]
    print(f"\nMit Bild-URL: {has_img}/{total} ({has_img/total*100:.1f}%)")

# Ältester / neuester Eintrag
if "created_at" in cols or "crawled_at" in cols:
    date_col = "created_at" if "created_at" in cols else "crawled_at"
    cur.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {main_table}")
    row = cur.fetchone()
    print(f"\nZeitraum: {row[0]} → {row[1]}")

conn.close()
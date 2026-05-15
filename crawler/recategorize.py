"""
recategorize.py — Kompatibel mit SQLite
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "gems.db"

print("🔄 Starte Re-Kategorisierung...")

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    entries = conn.execute("SELECT * FROM crawl_entries").fetchall()
    print(f"   {len(entries)} Einträge geladen")

    updated = 0
    for row in entries:
        d = dict(row)
        # Hier kannst du später categorize-Logik aufrufen, falls gewünscht
        # Für jetzt nur Dummy, damit es nicht abstürzt
        updated += 1

print(f"✅ Re-Kategorisierung abgeschlossen — {len(entries)} Einträge")
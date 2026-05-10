"""
DB — liest und schreibt crawl_db.json
Einzige Stelle die die Datenbankdatei kennt.
"""
import json
import os
from config import DB_PATH


def load_db() -> list:
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(entries: list) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"[db] {len(entries)} Einträge gespeichert → {DB_PATH}")


def add_entries(new_entries: list) -> int:
    """Fügt neue Einträge hinzu, überspringt Duplikate (per source_id).
    Gibt Anzahl neu hinzugefügter Einträge zurück."""
    db = load_db()
    existing_ids = {e["source_id"] for e in db}
    added = 0
    for entry in new_entries:
        if entry["source_id"] not in existing_ids:
            db.append(entry)
            existing_ids.add(entry["source_id"])
            added += 1
    save_db(db)
    return added


def get_stats() -> dict:
    """Gibt Statistiken über die Datenbank zurück."""
    db = load_db()
    sources = {}
    categories = {}
    for e in db:
        sources[e.get("source", "?")] = sources.get(e.get("source", "?"), 0) + 1
        cat = e.get("category", "?")
        categories[cat] = categories.get(cat, 0) + 1
    return {"total": len(db), "by_source": sources, "by_category": categories}

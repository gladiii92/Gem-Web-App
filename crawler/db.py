"""
db.py — SQLite Backend (ersetzt crawl_db.json)
Einzige Stelle die die Datenbankdatei kennt.
API identisch zu vorher: load_db(), save_db(), add_entries(), get_stats()
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "gems.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["colours"] = json.loads(d["colours"] or "[]")
    return d


# ---------------------------------------------------------------------------
# Public API — identisch zu vorher
# ---------------------------------------------------------------------------

def load_db() -> list:
    """Gibt alle Einträge als Liste von Dicts zurück (kompatibel zu JSON-Format)."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM crawl_entries ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]


def save_db(entries: list) -> None:
    """Bulk-Upsert: überschreibt vorhandene source_ids, fügt neue ein.
    Wird vom Crawler nach jedem Batch aufgerufen."""
    with _connect() as conn:
        conn.executemany("""
            INSERT INTO crawl_entries
                (source_id, source, price_type, name_raw, gem_category, category,
                 category_id, carat, clarity, treatment, origin, colours,
                 price_usd, currency_raw, image_url, lot_url, crawled_at)
            VALUES
                (:source_id,:source,:price_type,:name_raw,:gem_category,:category,
                 :category_id,:carat,:clarity,:treatment,:origin,:colours,
                 :price_usd,:currency_raw,:image_url,:lot_url,:crawled_at)
            ON CONFLICT(source_id) DO UPDATE SET
                clarity    = excluded.clarity,
                price_usd  = excluded.price_usd,
                colours    = excluded.colours,
                treatment  = excluded.treatment,
                origin     = excluded.origin,
                crawled_at = excluded.crawled_at
        """, [_prepare(e) for e in entries])
    print(f"[db] {len(entries)} Einträge gespeichert → {DB_PATH}")


def add_entries(new_entries: list) -> int:
    """Fügt neue Einträge hinzu, überspringt Duplikate (per source_id).
    Gibt Anzahl neu hinzugefügter Einträge zurück."""
    with _connect() as conn:
        existing = {r[0] for r in conn.execute("SELECT source_id FROM crawl_entries")}
        to_insert = [e for e in new_entries if e["source_id"] not in existing]
        if to_insert:
            conn.executemany("""
                INSERT OR IGNORE INTO crawl_entries
                    (source_id, source, price_type, name_raw, gem_category, category,
                     category_id, carat, clarity, treatment, origin, colours,
                     price_usd, currency_raw, image_url, lot_url, crawled_at)
                VALUES
                    (:source_id,:source,:price_type,:name_raw,:gem_category,:category,
                     :category_id,:carat,:clarity,:treatment,:origin,:colours,
                     :price_usd,:currency_raw,:image_url,:lot_url,:crawled_at)
            """, [_prepare(e) for e in to_insert])
    return len(to_insert)


def get_stats() -> dict:
    """Gibt Statistiken über die Datenbank zurück."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM crawl_entries").fetchone()[0]
        by_source = {r[0]: r[1] for r in conn.execute(
            "SELECT source, COUNT(*) FROM crawl_entries GROUP BY source")}
        by_category = {r[0]: r[1] for r in conn.execute(
            "SELECT category, COUNT(*) FROM crawl_entries GROUP BY category")}
    return {"total": total, "by_source": by_source, "by_category": by_category}


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _prepare(e: dict) -> dict:
    """Normalisiert einen Entry-Dict für SQLite (colours als JSON-String)."""
    d = dict(e)
    colours = d.get("colours")
    if isinstance(colours, list):
        d["colours"] = json.dumps(colours)
    elif colours is None:
        d["colours"] = "[]"
    # Felder die SQLite nicht kennt — ignorieren
    for key in list(d.keys()):
        if key not in {
            "source_id","source","price_type","name_raw","gem_category","category",
            "category_id","carat","clarity","treatment","origin","colours",
            "price_usd","currency_raw","image_url","lot_url","crawled_at"
        }:
            d.pop(key)
    return d
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

def load_db() -> list:
    """Gibt alle Einträge als Liste von Dicts zurück (kompatibel zu JSON-Format)."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM crawl_entries ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]

def save_db(entries: list) -> None:
    """Bulk-Upsert mit allen Feldern"""
    with _connect() as conn:
        conn.executemany("""
            INSERT INTO crawl_entries
                (source_id, source, price_type, name_raw, gem_category, category,
                 category_id, carat, clarity, treatment, origin, colours,
                 price_usd, currency_raw, image_url, lot_url, crawled_at,
                 description_raw, shape, cut, dimensions_mm, certificate)
            VALUES
                (:source_id,:source,:price_type,:name_raw,:gem_category,:category,
                 :category_id,:carat,:clarity,:treatment,:origin,:colours,
                 :price_usd,:currency_raw,:image_url,:lot_url,:crawled_at,
                 :description_raw,:shape,:cut,:dimensions_mm,:certificate)
            ON CONFLICT(source_id) DO UPDATE SET
                source          = excluded.source,
                price_type      = excluded.price_type,
                name_raw        = excluded.name_raw,
                gem_category    = excluded.gem_category,
                category        = excluded.category,
                category_id     = excluded.category_id,
                carat           = excluded.carat,
                clarity         = COALESCE(excluded.clarity, clarity),
                treatment       = COALESCE(excluded.treatment, treatment),
                origin          = COALESCE(excluded.origin, origin),
                colours         = COALESCE(excluded.colours, colours),
                price_usd       = COALESCE(excluded.price_usd, price_usd),
                currency_raw    = COALESCE(excluded.currency_raw, currency_raw),
                image_url       = COALESCE(excluded.image_url, image_url),
                lot_url         = COALESCE(excluded.lot_url, lot_url),
                crawled_at      = excluded.crawled_at,
                description_raw = COALESCE(excluded.description_raw, description_raw),
                shape           = COALESCE(excluded.shape, shape),
                cut             = COALESCE(excluded.cut, cut),
                dimensions_mm   = COALESCE(excluded.dimensions_mm, dimensions_mm),
                certificate     = COALESCE(excluded.certificate, certificate)
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
                     price_usd, currency_raw, image_url, lot_url, crawled_at,
                     description_raw, shape, cut, dimensions_mm, certificate)
                VALUES
                    (:source_id,:source,:price_type,:name_raw,:gem_category,:category,
                     :category_id,:carat,:clarity,:treatment,:origin,:colours,
                     :price_usd,:currency_raw,:image_url,:lot_url,:crawled_at,
                     :description_raw,:shape,:cut,:dimensions_mm,:certificate)
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

def _prepare(e: dict) -> dict:
    """Normalisiert einen Entry-Dict für SQLite — garantiert alle Felder."""
    DEFAULTS = {
        "source_id": None,
        "source": None,
        "price_type": None,
        "name_raw": None,
        "gem_category": None,
        "category": None,
        "category_id": None,
        "carat": None,
        "clarity": None,
        "treatment": None,
        "origin": None,
        "colours": "[]",
        "price_usd": None,
        "currency_raw": None,
        "image_url": None,
        "lot_url": None,
        "crawled_at": None,
        "description_raw": None,
        "shape": None,
        "cut": None,
        "dimensions_mm": None,
        "certificate": None,
    }

    d = {**DEFAULTS, **e}

    colours = d.get("colours")
    if isinstance(colours, list):
        d["colours"] = json.dumps(colours)
    elif colours is None:
        d["colours"] = "[]"

    return d
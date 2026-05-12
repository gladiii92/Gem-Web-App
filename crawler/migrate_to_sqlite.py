import json
import sqlite3
from pathlib import Path

DB_PATH    = Path(__file__).parent / "gems.db"
CRAWL_JSON = Path(__file__).parent / "crawl_db.json"
CORR_JSON  = Path(__file__).parent.parent / "vision" / "corrections.json"

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS crawl_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id   TEXT UNIQUE NOT NULL,
            source      TEXT NOT NULL,
            price_type  TEXT,
            name_raw    TEXT,
            gem_category TEXT,
            category    TEXT,
            category_id INTEGER,
            carat       REAL,
            clarity     TEXT,
            treatment   TEXT,
            origin      TEXT,
            colours     TEXT,
            price_usd   REAL,
            currency_raw TEXT,
            image_url   TEXT,
            lot_url     TEXT,
            crawled_at  TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_gem_category ON crawl_entries(gem_category);
        CREATE INDEX IF NOT EXISTS idx_clarity      ON crawl_entries(clarity);
        CREATE INDEX IF NOT EXISTS idx_source       ON crawl_entries(source);
        CREATE INDEX IF NOT EXISTS idx_carat        ON crawl_entries(carat);

        CREATE TABLE IF NOT EXISTS corrections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            predicted   TEXT NOT NULL,
            correct     TEXT NOT NULL,
            image_hash  TEXT,
            timestamp   TEXT,
            session_id  TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_predicted ON corrections(predicted);
        CREATE INDEX IF NOT EXISTS idx_correct   ON corrections(correct);
    """)

def migrate_crawl(conn):
    with open(CRAWL_JSON, encoding="utf-8") as f:
        entries = json.load(f)

    rows = []
    for e in entries:
        rows.append((
            e["source_id"],
            e.get("source"),
            e.get("price_type"),
            e.get("name_raw"),
            e.get("gem_category"),
            e.get("category"),
            e.get("category_id"),
            e.get("carat"),
            e.get("clarity"),
            e.get("treatment"),
            e.get("origin"),
            json.dumps(e.get("colours") or []),
            e.get("price_usd"),
            e.get("currency_raw"),
            e.get("image_url"),
            e.get("lot_url"),
            e.get("crawled_at"),
        ))

    conn.executemany("""
        INSERT OR IGNORE INTO crawl_entries
        (source_id, source, price_type, name_raw, gem_category, category,
         category_id, carat, clarity, treatment, origin, colours,
         price_usd, currency_raw, image_url, lot_url, crawled_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    return len(rows)

def migrate_corrections(conn):
    if not CORR_JSON.exists():
        print("corrections.json nicht gefunden — überspringe.")
        return 0

    with open(CORR_JSON, encoding="utf-8") as f:
        entries = json.load(f)

    rows = [(
        e["predicted"],
        e["correct"],
        e.get("image_hash"),
        e.get("timestamp"),
        e.get("session_id"),
    ) for e in entries]

    conn.executemany("""
        INSERT INTO corrections (predicted, correct, image_hash, timestamp, session_id)
        VALUES (?,?,?,?,?)
    """, rows)
    return len(rows)

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    init_db(conn)
    n_crawl = migrate_crawl(conn)
    n_corr  = migrate_corrections(conn)
    conn.commit()
    conn.close()

    print(f"Migration abgeschlossen:")
    print(f"  crawl_entries : {n_crawl} Eintraege")
    print(f"  corrections   : {n_corr} Eintraege")
    print(f"  DB gespeichert: {DB_PATH}")
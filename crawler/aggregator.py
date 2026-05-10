"""
aggregator.py — crawl_db.json → data.json
Schreibt _crawler_stats pro Karat-Bucket.
Mit Clarity wenn verfügbar, sonst gesamt.
"""

import json
import statistics
from pathlib import Path

ROOT      = Path(__file__).parent.parent
CRAWL_DB  = Path(__file__).parent / "crawl_db.json"
DATA_JSON = ROOT / "data.json"

CATEGORY_MAP = {
    "Katlang Topaz (Imperial Orange/Pink)":               1,
    "Grossular Garnet/Granat (Green)":                    2,
    "Grossular Garnet/Granat (Yellowish Green)":          3,
    "Tsavorit Garnet/Granat (Yellowish Green)":           4,
    "Saphir (Weiß, Sri Lanka)":                           5,
    "Tanzanit (Bluish Violet)":                           6,
    "Tanzanit (Violetish Blue)":                          7,
    "Grossular Garnet/Granat (Mandarin/Orange)":          8,
    "Demantoid Garnet/Granat (Green)":                    9,
    "Saphir (Gelb, Sri Lanka)":                          10,
    "Tsavorit Garnet/Granat (Green)":                    11,
    "Demantoid Garnet/Granat (Yellowish Green)":         12,
    "Saphir (Purple, Sri Lanka)":                        13,
    "Spinell (Blau/Purple)":                             14,
    "Saphir (Grün/Teal, Sri Lanka)":                     15,
    "Spinell (Orange)":                                  16,
    "Saphir (Pink, Sri Lanka)":                          17,
    "Smaragd (Grün, Overall)":                           18,
    "Rubin (Purplish Red / Reddish Purple)":             19,
    "Spinell (NormalRot & Jedi(Pink) & Kobaltblau)":     20,
    "Rubin (Red, Sri Lanka)":                            21,
    "Alexandrit (Blue/Green - Purple/Red)":              22,
    "Alexandrit (Yellow/Green - Red/Orange)":            23,
    "Padparadscha Saphir (Pink-Orange, Sri Lanka)":      24,
    "Saphir (Blau, Sri Lanka)":                          25,
    "Paraiba Tourmaline (Greenish Blue)":                26,
    "Paraiba Tourmaline (Bluish Green)":                 27,
}

CLARITY_GRADES = ["I1", "SI2", "SI1", "VS", "VVS"]

with open(CRAWL_DB, "r", encoding="utf-8") as f:
    entries = json.load(f)

with open(DATA_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# ── Gruppiere: { data_id: [ {carat, price, price_type, clarity}, ... ] } ──────
raw = {}
for e in entries:
    cat   = e.get("category", "")
    price = e.get("price_usd")
    carat = e.get("carat")
    ptype = e.get("price_type")

    if not cat or cat.startswith("unknown") or not price or not carat:
        continue
    if price <= 0 or carat <= 0:
        continue

    data_id = CATEGORY_MAP.get(cat)
    if not data_id:
        continue

    raw.setdefault(data_id, []).append({
        "carat":   float(carat),
        "price":   float(price),
        "type":    ptype,
        "clarity": e.get("clarity"),  # kann None sein
    })

# ── Statistik ─────────────────────────────────────────────────────────────────
def calc_stats(prices: list) -> dict | None:
    if not prices:
        return None
    return {
        "min":    round(min(prices), 2),
        "max":    round(max(prices), 2),
        "median": round(statistics.median(prices), 2),
        "n":      len(prices),
    }

def bucket_entries(items, carat_min, carat_max):
    return [x for x in items if carat_min <= x["carat"] <= carat_max]

# ── Patche data.json ──────────────────────────────────────────────────────────
updated_gems    = 0
updated_buckets = 0

for gem in data:
    gid   = gem.get("id")
    items = raw.get(gid, [])
    if not items:
        continue

    updated_gems += 1

    for bucket in gem.get("price_ranges", []):
        cmin = bucket.get("carat_min", 0)
        cmax = bucket.get("carat_max", 9999)

        if cmin >= 15:
            continue

        b_items = bucket_entries(items, cmin, cmax)
        if not b_items:
            continue

        stats = {"source": "gemrock"}

        # ── Gesamt-Stats (alle Clarity) ───────────────────────────────────────
        retail_all    = [x["price"] for x in b_items if x["type"] == "retail"]
        wholesale_all = [x["price"] for x in b_items if x["type"] == "wholesale"]

        r = calc_stats(retail_all)
        w = calc_stats(wholesale_all)
        if r:
            stats["retail"]    = r
        if w:
            stats["wholesale"] = w

        # ── Per-Clarity-Stats (nur wenn genug Samples) ───────────────────────
        clarity_stats = {}
        for grade in CLARITY_GRADES:
            grade_items   = [x for x in b_items if x["clarity"] == grade]
            retail_grade  = [x["price"] for x in grade_items if x["type"] == "retail"]
            ws_grade      = [x["price"] for x in grade_items if x["type"] == "wholesale"]

            entry = {}
            r = calc_stats(retail_grade)
            w = calc_stats(ws_grade)
            if r:
                entry["retail"] = r
            if w:
                entry["wholesale"] = w
            if entry:
                clarity_stats[grade] = entry

        if clarity_stats:
            stats["by_clarity"] = clarity_stats

        bucket["_crawler_stats"] = stats
        updated_buckets += 1

# ── Globale Flat-Felder (für Dashboard-Übersicht) ─────────────────────────────
for gem in data:
    gid   = gem.get("id")
    items = raw.get(gid, [])
    if not items:
        continue

    retail_prices    = [x["price"] for x in items if x["type"] == "retail"]
    wholesale_prices = [x["price"] for x in items if x["type"] == "wholesale"]

    r = calc_stats(retail_prices)
    w = calc_stats(wholesale_prices)

    if r:
        gem["retail_price_min"]    = r["min"]
        gem["retail_price_max"]    = r["max"]
        gem["retail_price_median"] = r["median"]
        gem["retail_sample_count"] = r["n"]
        gem["_retail_source"]      = "crawler"
    if w:
        gem["wholesale_price_min"]    = w["min"]
        gem["wholesale_price_max"]    = w["max"]
        gem["wholesale_price_median"] = w["median"]
        gem["wholesale_sample_count"] = w["n"]
        gem["_wholesale_source"]      = "crawler"

# ── Schreibe data.json ────────────────────────────────────────────────────────
with open(DATA_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# ── Report ────────────────────────────────────────────────────────────────────
print(f"\n✅ Aggregation abgeschlossen")
print(f"   Kategorien mit Daten     : {updated_gems}/27")
print(f"   Karat-Buckets befüllt    : {updated_buckets}")

print(f"\nBeispiel — Alexandrit [22] Bucket-Stats:")
alex = next((g for g in data if g["id"] == 22), None)
if alex:
    for b in alex.get("price_ranges", []):
        cs = b.get("_crawler_stats", {})
        r  = cs.get("retail", {})
        if not r:
            continue
        by_c = cs.get("by_clarity", {})
        clarity_info = ", ".join(
            f"{g}:n={v['retail']['n']}" for g, v in by_c.items() if "retail" in v
        ) or "keine Clarity-Daten"
        print(f"  {b['carat_min']:>5}–{b['carat_max']:<6}ct  "
              f"gesamt n={r['n']:>3}  Median=${r['median']:>7,.0f}  "
              f"| Clarity: {clarity_info}")
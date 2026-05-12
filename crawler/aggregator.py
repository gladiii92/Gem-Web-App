"""
aggregator.py — crawl_db.json → data.json
Schreibt _crawler_stats pro Karat-Bucket.
Mit Clarity wenn verfügbar, sonst gesamt.
"""

import json
import statistics
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from db import load_db

ROOT      = Path(__file__).parent.parent
DATA_JSON = ROOT / "data.json"

CATEGORY_MAP = {
    "Katlang Topaz (Imperial Orange/Pink)":           1,
    "Grossular Garnet/Granat (Green)":                2,
    "Grossular Garnet/Granat (Yellowish Green)":      3,
    "Tsavorit Garnet/Granat (Yellowish Green)":       4,
    "Saphir (Weiß, Sri Lanka)":                       5,
    "Tanzanit (Bluish Violet)":                       6,
    "Tanzanit (Violetish Blue)":                      7,
    "Grossular Garnet/Granat (Mandarin/Orange)":      8,
    "Demantoid Garnet/Granat (Green)":                9,
    "Saphir (Gelb, Sri Lanka)":                      10,
    "Tsavorit Garnet/Granat (Green)":                11,
    "Demantoid Garnet/Granat (Yellowish Green)":     12,
    "Saphir (Purple, Sri Lanka)":                    13,
    "Spinell (Blau/Purple)":                         14,
    "Saphir (Grün/Teal, Sri Lanka)":                 15,
    "Spinell (Orange)":                              16,
    "Saphir (Pink, Sri Lanka)":                      17,
    "Smaragd (Grün, Overall)":                       18,
    "Rubin (Purplish Red / Reddish Purple)":         19,
    "Spinell (NormalRot & Jedi(Pink) & Kobaltblau)": 20,
    "Rubin (Red, Sri Lanka)":                        21,
    "Alexandrit (Blue/Green - Purple/Red)":          22,
    "Alexandrit (Yellow/Green - Red/Orange)":        23,
    "Padparadscha Saphir (Pink-Orange, Sri Lanka)":  24,
    "Saphir (Blau, Sri Lanka)":                      25,
    "Paraiba Tourmaline (Greenish Blue)":            26,
    "Paraiba Tourmaline (Bluish Green)":             27,
    "Rubellite (Pink/Red)":                          28,
    "Indicolite (Blue/Blue-Green)":                  29,
    "Chrome Tourmaline (Green)":                     30,
    "Watermelon Tourmaline (Pink/Green)":            31,
    "Rhodolite Garnet (Pink/Purple)":                32,
    "Malaya Garnet (Orange/Pink)":                   33,
    "Color-Change Garnet":                           34,
    "Pyrope Garnet (Red)":                           35,
    "Almandine Garnet (Deep Red)":                   36,
    "Morganite (Pink/Peach)":                        37,
}

CLARITY_GRADES = ["I1", "SI2", "SI1", "VS", "VVS"]

entries = load_db()

with open(DATA_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# ── Gruppiere: { data_id: [ {carat, price, price_type, clarity, source}, ... ] }
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
        "clarity": e.get("clarity"),
        "source":  e.get("source", "unknown"),  # "gemrock" oder "1stdibs"
    })

# ── Statistik ─────────────────────────────────────────────────────────────────
def calc_stats(prices: list) -> dict | None:
    if not prices:
        return None

    n_raw = len(prices)

    if n_raw >= 4:
        sorted_p = sorted(prices)
        q1 = statistics.quantiles(sorted_p, n=4)[0]
        q3 = statistics.quantiles(sorted_p, n=4)[2]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        filtered = [p for p in sorted_p if lower <= p <= upper]
    else:
        filtered = prices

    outliers_removed = n_raw - len(filtered)

    return {
        "min":              round(min(filtered), 2),
        "max":              round(max(filtered), 2),
        "median":           round(statistics.median(filtered), 2),
        "n":                len(filtered),
        "n_raw":            n_raw,
        "outliers_removed": outliers_removed,
    }

def bucket_entries(items, carat_min, carat_max):
    return [x for x in items if carat_min <= x["carat"] <= carat_max]

def build_source_stats(items: list) -> dict:
    """Berechnet retail/wholesale + by_clarity für eine Quellliste."""
    stats = {}

    retail_all    = [x["price"] for x in items if x["type"] == "retail"]
    wholesale_all = [x["price"] for x in items if x["type"] == "wholesale"]

    r = calc_stats(retail_all)
    w = calc_stats(wholesale_all)
    if r:
        stats["retail"] = r
    if w:
        stats["wholesale"] = w

    clarity_stats = {}
    for grade in CLARITY_GRADES:
        grade_items  = [x for x in items if x["clarity"] == grade]
        retail_grade = [x["price"] for x in grade_items if x["type"] == "retail"]
        ws_grade     = [x["price"] for x in grade_items if x["type"] == "wholesale"]
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

    return stats

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

        # ── Source-Split
        gemrock_items  = [x for x in b_items if x["source"] == "gemrock"]
        stdibs_items   = [x for x in b_items if x["source"] == "1stdibs"]

        by_source = {}
        if gemrock_items:
            gs = build_source_stats(gemrock_items)
            if gs:
                by_source["gemrock"] = gs
        if stdibs_items:
            ss = build_source_stats(stdibs_items)
            if ss:
                by_source["1stdibs"] = ss

        if by_source:
            bucket["_crawler_stats"] = {"by_source": by_source}
            updated_buckets += 1

# ── Globale Flat-Felder (kombiniert über alle Quellen) ────────────────────────
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
print(f"   Kategorien mit Daten     : {updated_gems}/37")
print(f"   Karat-Buckets befüllt    : {updated_buckets}")

print(f"\nBeispiel — Alexandrit [22] Bucket-Stats:")
alex = next((g for g in data if g["id"] == 22), None)
if alex:
    for b in alex.get("price_ranges", []):
        cs = b.get("_crawler_stats", {})
        by_source = cs.get("by_source", {})
        for src, src_stats in by_source.items():
            r = src_stats.get("retail", {})
            if not r:
                continue
            by_c = src_stats.get("by_clarity", {})
            clarity_info = ", ".join(
                f"{g}:n={v['retail']['n']}" for g, v in by_c.items() if "retail" in v
            ) or "keine Clarity-Daten"
            print(f"  [{src:8}] {b['carat_min']:>5}–{b['carat_max']:<6}ct "
                  f"n={r['n']:>3} Median=${r['median']:>7,.0f} | {clarity_info}")
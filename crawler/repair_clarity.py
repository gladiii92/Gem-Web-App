"""
repair_clarity.py — Repair-Run für alle NULL-Felder aus GemRock/1stDibs Detailseiten.
Zieht: clarity, treatment, origin, shape, cut, dimensions_mm,
       color_code, quality_grade, description_raw

Resume: description_raw IS NULL = noch nicht besucht
Idempotent: bestehende Werte werden NICHT überschrieben.

Zusatz:
- Cabochon-Steine werden ausgeschlossen.
- GemRock description_raw beginnt erst am relevanten Produktblock.
- 1stDibs description_raw kommt aus JSON-LD.
"""
import re
import sys
import json
import time
import sqlite3
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path(__file__).parent / "gems.db"
BATCH_COMMIT = 50
DELAY_GEMROCK = 0.8
DELAY_1STDIBS = 2.0

CLARITY_MAP = {
    "loupe clean": "VVS",
    "loupe-clean": "VVS",
    "flawless": "VVS",
    "vvs": "VVS",
    "eye clean": "SI1",
    "eyeclean": "SI1",
    "eye-clean": "SI1",
    " vs ": "VS",
    "vs but": "VS",
    "clarity: vs": "VS",
    "clarity: vvs": "VVS",
    "clarity: si1": "SI1",
    "clarity: si2": "SI2",
    "clarity: i1": "I1",
    "clarity. : vvs": "VVS",
    "clarity. : vs": "VS",
    "clarity. : si1": "SI1",
    "clarity. : si2": "SI2",
    "si1": "SI1",
    "si2": "SI2",
    " i1 ": "I1",
    "slightly included": "SI2",
    "heavily included": "I1",
    "n/a": "unknown",
    "not available": "unknown",
    "not specified": "unknown",
    "not graded": "unknown",
}

TREATMENT_UNHEATED = [
    "no treatment", "no heat", "unheated", "untreated",
    "treatments: none", "treatment: none", "treatment-none", "treatment : none"
]
TREATMENT_HEATED = [
    "heated", "heat treatment", "beryllium", "glass filled", "glass-filled"
]

ORIGINS = [
    "Sri Lanka", "Ceylon", "Burma", "Myanmar", "Colombia", "Brazil",
    "Tanzania", "Madagascar", "Mozambique", "Afghanistan", "Russia",
    "Thailand", "Vietnam", "Kenya", "Cambodia", "Kashmir",
    "Australia", "Zambia", "Zimbabwe", "Pakistan", "Nigeria"
]

SHAPES = [
    "oval", "round", "cushion", "pear", "emerald cut", "heart",
    "marquise", "radiant", "princess", "shield", "square",
    "rectangle", "octagon", "triangle", "briolette", "cabochon",
    "free shape", "freeform"
]

CUTS = [
    "faceted", "cabochon", "mixed cut", "brilliant", "step cut",
    "portuguese", "checkerboard", "rose cut", "shield"
]

def _parse_clarity(text: str) -> str | None:
    t = text.lower()
    for keyword, grade in CLARITY_MAP.items():
        if keyword in t:
            return grade
    return None

def _parse_treatment(text: str) -> str | None:
    t = text.lower()
    if any(k in t for k in TREATMENT_UNHEATED):
        return "unheated"
    if any(k in t for k in TREATMENT_HEATED):
        return "heated"
    return None

def _parse_origin(text: str) -> str | None:
    for origin in ORIGINS:
        if origin.lower() in text.lower():
            return "Sri Lanka" if origin == "Ceylon" else origin
    return None

def _parse_shape(text: str) -> str | None:
    t = text.lower()
    for shape in SHAPES:
        if shape in t:
            return shape
    return None

def _parse_shape_from_label(text: str) -> str | None:
    m = re.search(r'[Ss]hape\s*[.:]?\s*[:\s]\s*([a-zA-Z\s]+?)(?:\n|\s{2,}|\.|$)', text)
    if m:
        val = m.group(1).strip().lower()
        for shape in SHAPES:
            if shape in val:
                return shape
        if len(val) < 20:
            return val
    return None

def _parse_cut(text: str) -> str | None:
    t = text.lower()
    for cut in CUTS:
        if cut in t:
            return cut
    return None

def _parse_dimensions(text: str) -> str | None:
    m = re.search(r'(\d+\.?\d*\s*x\s*\d+\.?\d*\s*x\s*\d+\.?\d*\s*(?:mm)?)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def _parse_color_code(text: str) -> str | None:
    m = re.search(r'[Cc]olou?r\s*[.:]?\s*[:\s]\s*([^\n\r:,]{3,40}?)(?:\s{2,}|\n|[A-Z][a-z]+\s*:|$)', text)
    if m:
        val = m.group(1).strip()
        if len(val) < 40 and not any(x in val.lower() for x in ["shipping", "certificate", "shape", "http"]):
            return val
    return None

def _parse_quality_grade(text: str) -> str | None:
    m = re.search(r'[Qq]uality\s+[Gg]rade[:\s]+(\d+(?:\.\d+)?)', text)
    if m:
        return m.group(1)
    return None

def _extract_description_block(full_text: str) -> str:
    cut = re.search(r'Show details\s+Details\s+Necessary', full_text)
    if cut:
        full_text = full_text[cut.end():].strip()

    m = re.search(
        r'(\d+(?:\.\d+)?\s*carat.*?Colours\s+Description)',
        full_text,
        re.IGNORECASE | re.DOTALL
    )
    if m:
        full_text = full_text[m.start():]

    end = re.search(r'(?:Shipping\s+Provider\s+Destination\s+Cost|Provider\s+Destination\s+Cost)', full_text)
    if end:
        full_text = full_text[:end.start()]

    return full_text.strip()

def _accept_cookies(page):
    try:
        page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=4000)
        page.wait_for_timeout(1000)
        return
    except Exception:
        pass
    try:
        for btn in page.locator("button").all():
            try:
                txt = btn.inner_text(timeout=300).strip().lower()
                if txt in ("allow all", "accept all", "allow all cookies", "accept all cookies"):
                    btn.click()
                    page.wait_for_timeout(1000)
                    return
            except Exception:
                continue
    except Exception:
        pass

def _is_cabochon_text(text: str) -> bool:
    return "cabochon" in text.lower()

def fetch_detail_fields_gemrock(page, lot_url: str) -> dict:
    empty = {
        "clarity": None, "treatment": None, "origin": None,
        "shape": None, "cut": None, "dimensions_mm": None,
        "color_code": None, "quality_grade": None, "description_raw": None
    }
    if not lot_url:
        return empty

    full_url = lot_url if lot_url.startswith("http") else f"https://www.gemrockauctions.com{lot_url}"

    try:
        page.goto(full_url, wait_until="domcontentloaded", timeout=12000)
        try:
            page.wait_for_selector("dt", timeout=5000)
        except PlaywrightTimeout:
            pass
    except PlaywrightTimeout:
        pass

    page.wait_for_timeout(1500)
    soup = BeautifulSoup(page.content(), "lxml")

    dt_data = {}
    seen_labels = set()
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True).lower()
        dd = dt.find_next_sibling("dd")
        val = dd.get_text(" ", strip=True) if dd else ""
        if label and label not in seen_labels and val:
            seen_labels.add(label)
            dt_data[label] = val

    result = dict(empty)

    if "clarity" in dt_data:
        result["clarity"] = _parse_clarity(dt_data["clarity"])
    if "treatment" in dt_data:
        result["treatment"] = _parse_treatment(dt_data["treatment"])
    if "type" in dt_data:
        result["cut"] = _parse_cut(dt_data["type"]) or dt_data["type"].lower()
    if "shape" in dt_data:
        result["shape"] = _parse_shape(dt_data["shape"]) or dt_data["shape"].lower()
    if "dimensions (mm)" in dt_data:
        result["dimensions_mm"] = _parse_dimensions(dt_data["dimensions (mm)"]) or dt_data["dimensions (mm)"]

    full_text = re.sub(r'\s+', ' ', soup.get_text(" ")).strip()
    desc = _extract_description_block(full_text)

    if desc:
        result["description_raw"] = desc[:1500]
        if result["clarity"] is None: result["clarity"] = _parse_clarity(desc)
        if result["treatment"] is None: result["treatment"] = _parse_treatment(desc)
        if result["origin"] is None: result["origin"] = _parse_origin(desc)
        if result["shape"] is None: result["shape"] = _parse_shape_from_label(desc) or _parse_shape(desc)
        if result["cut"] is None: result["cut"] = _parse_cut(desc)
        if result["dimensions_mm"] is None: result["dimensions_mm"] = _parse_dimensions(desc)
        if result["color_code"] is None: result["color_code"] = _parse_color_code(desc)
        if result["quality_grade"] is None: result["quality_grade"] = _parse_quality_grade(desc)
    else:
        result["description_raw"] = "N/A"

    return result

def fetch_detail_fields_1stdibs(page, lot_url: str) -> dict:
    empty = {
        "clarity": None, "treatment": None, "origin": None,
        "shape": None, "cut": None, "dimensions_mm": None,
        "color_code": None, "quality_grade": None, "description_raw": None
    }
    try:
        page.goto(lot_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        html = page.content()

        desc = ""
        matches = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        for raw in matches:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    data = data[0]
                if data.get("@type") == "Product" and data.get("description"):
                    desc = data["description"][:1500]
                    break
            except Exception:
                continue

        if not desc:
            clean = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()
            desc = clean[500:1500]

        if not desc:
            desc = "N/A"

        return {
            "clarity": _parse_clarity(desc),
            "treatment": _parse_treatment(desc),
            "origin": _parse_origin(desc),
            "shape": _parse_shape_from_label(desc) or _parse_shape(desc),
            "cut": _parse_cut(desc),
            "dimensions_mm": _parse_dimensions(desc),
            "color_code": _parse_color_code(desc),
            "quality_grade": None,
            "description_raw": desc,
        }
    except Exception as e:
        print(f"    [ERROR] {lot_url}: {e}")
        return empty

def _debug(source_id, fields):
    filled = {k: v for k, v in fields.items() if v is not None and k != "description_raw"}
    null_fields = [k for k, v in fields.items() if v is None and k != "description_raw"]
    has_desc = "✓desc" if fields.get("description_raw") and fields["description_raw"] != "N/A" else "✗desc"
    icon = "✅" if filled else "❌"
    print(f"  [{icon}] {source_id} {has_desc}")
    if filled:
        print(f"    Gefunden:  {filled}")
    if null_fields:
        print(f"    NULL:      {null_fields}")

REPAIR_FIELDS = ["clarity", "treatment", "origin", "shape", "cut",
                 "dimensions_mm", "color_code", "quality_grade", "description_raw"]

def repair_source(conn, page, source: str, fetch_fn, delay: float, limit: int):
    query = f"""
        SELECT source_id, lot_url, {', '.join(REPAIR_FIELDS)}
        FROM crawl_entries
        WHERE source = '{source}' AND lot_url IS NOT NULL
        AND description_raw IS NULL
        ORDER BY source_id
    """
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    total = len(rows)
    print(f"\n[{source}] {total} Einträge noch nicht besucht{' (Limit: '+str(limit)+')' if limit else ''}")

    improved = 0
    for i, row in enumerate(rows):
        source_id = row[0]
        lot_url = row[1]
        current = dict(zip(REPAIR_FIELDS, row[2:]))

        fields = fetch_fn(page, lot_url)

        if _is_cabochon_text(fields.get("description_raw", "")) or _is_cabochon_text(fields.get("cut", "")):
            print(f"  [SKIP] {source_id} Cabochon entdeckt")
            continue

        _debug(source_id, fields)

        updates = {}
        for field in REPAIR_FIELDS:
            if current[field] is None and fields.get(field) is not None:
                updates[field] = fields[field]

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [source_id]
            conn.execute(f"UPDATE crawl_entries SET {set_clause} WHERE source_id = ?", values)
            improved += 1

        if i > 0 and i % BATCH_COMMIT == 0:
            conn.commit()
            print(f"  [commit] {i}/{total} verarbeitet — {improved} verbessert")

        time.sleep(delay)

    conn.commit()
    print(f"[{source}] ✅ Fertig — {improved}/{total} Einträge verbessert")

def print_stats(conn):
    print("\n=== NULL-Rate nach Repair ===")
    for source in ("gemrock", "1stdibs"):
        total = conn.execute(f"SELECT COUNT(*) FROM crawl_entries WHERE source='{source}'").fetchone()[0]
        for field in REPAIR_FIELDS:
            nulls = conn.execute(f"SELECT COUNT(*) FROM crawl_entries WHERE source='{source}' AND {field} IS NULL").fetchone()[0]
            pct = round(nulls / total * 100, 1) if total else 0
            bar = "█" * int((1 - nulls/total) * 20) if total else ""
            print(f"  {source:10} | {field:15} | NULL: {nulls:4}/{total} ({pct:5.1f}%) {bar}")

def run(source: str, limit: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = context.new_page()

        if source in ("gemrock", "all"):
            try:
                page.goto("https://www.gemrockauctions.com", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(2000)
                _accept_cookies(page)
                page.wait_for_timeout(1500)
            except Exception:
                pass
            repair_source(conn, page, "gemrock", fetch_detail_fields_gemrock, DELAY_GEMROCK, limit)

        if source in ("1stdibs", "all"):
            try:
                page.goto("https://www.1stdibs.com", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                page.wait_for_timeout(1000)
            except Exception:
                pass
            repair_source(conn, page, "1stdibs", fetch_detail_fields_1stdibs, DELAY_1STDIBS, limit)

        browser.close()

    print_stats(conn)
    conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["gemrock", "1stdibs", "all"], default="gemrock")
    ap.add_argument("--limit", type=int, default=0, help="0 = alle, N = Test-Modus mit N Einträgen")
    args = ap.parse_args()
    run(args.source, args.limit)
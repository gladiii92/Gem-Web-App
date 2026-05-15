"""
1stdibs_crawler.py — Retail-Preise von 1stDibs (v3)

Verbesserungen:
- Vollständige Detail-Extraktion (clarity, treatment, origin, shape, cut, dimensions, description_raw)
- Bessere Parser aus repair_clarity.py integriert
- description_raw aus JSON-LD + Fallback
"""

import re
import time
import subprocess
import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

from db import load_db, save_db
from categorizer import categorize

EUR_TO_USD = 1.08

# ---------------------------------------------------------------------------
# Stone URLs
# ---------------------------------------------------------------------------
STONE_URLS = {
    "sapphire":    "https://www.1stdibs.com/jewelry/loose-gemstones/stone/sapphire/",
    "ruby":        "https://www.1stdibs.com/jewelry/loose-gemstones/stone/ruby/",
    "emerald":     "https://www.1stdibs.com/jewelry/loose-gemstones/stone/emerald/",
    "alexandrite": "https://www.1stdibs.com/jewelry/loose-gemstones/stone/alexandrite/",
    "spinel":      "https://www.1stdibs.com/jewelry/loose-gemstones/stone/spinel/",
    "tanzanite":   "https://www.1stdibs.com/jewelry/loose-gemstones/stone/tanzanite/",
    "tourmaline":  "https://www.1stdibs.com/jewelry/loose-gemstones/stone/tourmaline/",
    "garnet":      "https://www.1stdibs.com/jewelry/loose-gemstones/stone/garnet/",
    "topaz":       "https://www.1stdibs.com/jewelry/loose-gemstones/stone/topaz/",
    "morganite":   "https://www.1stdibs.com/jewelry/loose-gemstones/stone/morganite/",
}

MAX_PAGES = 20


# ---------------------------------------------------------------------------
# Parser-Funktionen (aus repair_clarity.py übernommen + erweitert)
# ---------------------------------------------------------------------------

def _parse_clarity(text: str) -> str | None:
    if not text: return None
    t = text.lower()
    map_ = {
        "loupe clean": "VVS", "loupe-clean": "VVS", "flawless": "VVS", "vvs": "VVS",
        "eye clean": "SI1", "eyeclean": "SI1", "eye-clean": "SI1",
        " vs ": "VS", "si1": "SI1", "si2": "SI2", " i1 ": "I1",
        "clarity: vvs": "VVS", "clarity: vs": "VS", "clarity: si1": "SI1"
    }
    for k, v in map_.items():
        if k in t:
            return v
    return None


def _parse_treatment(text: str) -> str | None:
    if not text: return None
    t = text.lower()
    if any(x in t for x in ["no treatment", "no heat", "unheated", "untreated", "natural"]):
        return "unheated"
    if any(x in t for x in ["heated", "heat treatment", "beryllium", "glass filled", "glass-filled"]):
        return "heated"
    return None


def _parse_origin(text: str) -> str | None:
    origins = ["sri lanka", "ceylon", "burma", "myanmar", "colombia", "brazil", "tanzania",
               "madagascar", "mozambique", "afghanistan", "russia", "thailand", "vietnam"]
    t = text.lower()
    for o in origins:
        if o in t:
            return "Sri Lanka" if o == "ceylon" else o.title()
    return None


def _parse_shape(text: str) -> str | None:
    shapes = ["oval", "round", "cushion", "pear", "emerald", "heart", "marquise", "radiant"]
    t = text.lower()
    for s in shapes:
        if s in t:
            return s
    return None


def _parse_dimensions(text: str) -> str | None:
    m = re.search(r'(\d+\.?\d*\s*x\s*\d+\.?\d*\s*x\s*\d+\.?\d*\s*(?:mm)?)', text, re.I)
    return m.group(1).strip() if m else None


def fetch_detail_fields_1stdibs(page, lot_url: str) -> dict:
    """Verbesserte Detail-Extraktion für 1stDibs"""
    empty = {
        "clarity": None, "treatment": None, "origin": None,
        "shape": None, "cut": None, "dimensions_mm": None,
        "description_raw": None
    }
    try:
        page.goto(lot_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        html = page.content()

        # JSON-LD Description (beste Quelle)
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
                    desc = data["description"]
                    break
            except:
                continue

        # Fallback
        if not desc:
            desc = re.sub(r'<[^>]+>', ' ', html)[:2500]

        clean_desc = re.sub(r'\s+', ' ', desc).strip()

        return {
            "clarity": _parse_clarity(clean_desc),
            "treatment": _parse_treatment(clean_desc),
            "origin": _parse_origin(clean_desc),
            "shape": _parse_shape(clean_desc),
            "cut": None,  # selten verfügbar
            "dimensions_mm": _parse_dimensions(clean_desc),
            "description_raw": clean_desc[:2500],
        }
    except Exception as e:
        print(f"    [ERROR] 1stDibs Detail: {lot_url} → {e}")
        return empty


# ---------------------------------------------------------------------------
# Listing + Detail Parsing
# ---------------------------------------------------------------------------

def get_price_from_page(page) -> float | None:
    try:
        text = page.locator('[data-tn="price-amount"]').first.inner_text(timeout=4000)
        is_eur = '€' in text
        clean = float(re.sub(r'[^\d.]', '', text.replace(',', '')))
        return round(clean * EUR_TO_USD, 2) if is_eur else clean
    except:
        return None


def parse_weight(text: str) -> float | None:
    match = re.search(r'Weight:\s*([\d.,]+)\s*Carat', text, re.I) or re.search(r'([\d.,]+)\s*ct\b', text, re.I)
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except:
            return None
    return None


def title_from_url(url: str) -> str:
    match = re.search(r'/loose-gemstones/([^/]+)/id-j_', url)
    return match.group(1).replace('-', ' ').title() if match else ""


def parse_detail_page(page, url: str, gem_category: str) -> dict | None:
    """Haupt-Parser mit voller Detail-Extraktion"""
    try:
        price = get_price_from_page(page)
        if not price:
            return None

        html = page.content()
        full_text = re.sub(r'<[^>]+>', ' ', html)

        carat = parse_weight(full_text)
        if not carat:
            return None

        id_match = re.search(r'id-(j_\w+)', url)
        source_id = f"1stdibs_{id_match.group(1)}" if id_match else None

        # Neue erweiterte Felder
        extra = fetch_detail_fields_1stdibs(page, url)

        entry = {
            "source_id":   source_id,
            "source":      "1stdibs",
            "price_type":  "retail",
            "name_raw":    title_from_url(url),
            "gem_category": gem_category,
            "category":    None,
            "carat":       carat,
            "clarity":     extra["clarity"],
            "treatment":   extra["treatment"],
            "origin":      extra["origin"],
            "shape":       extra["shape"],
            "dimensions_mm": extra["dimensions_mm"],
            "colours":     [],
            "price_usd":   price,
            "currency_raw": "USD",
            "image_url":   None,
            "lot_url":     url,
            "description_raw": extra["description_raw"],
            "crawled_at":  datetime.now(timezone.utc).isoformat(),
        }

        return categorize(entry)

    except Exception as ex:
        print(f"  [parse] Fehler bei {url}: {ex}")
        return None


# ---------------------------------------------------------------------------
# URL Collection
# ---------------------------------------------------------------------------

def collect_product_urls(page, list_url: str, max_pages: int = MAX_PAGES) -> list[str]:
    urls = set()
    for p_num in range(1, max_pages + 1):
        url = list_url if p_num == 1 else f"{list_url}?page={p_num}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            html = page.content()
            found = re.findall(r'href="(/jewelry/loose-gemstones/[^"]+/id-j_[^"]+)"', html)
            new = {f"https://www.1stdibs.com{u}" for u in found}
            urls |= new
            print(f"  [list p{p_num}] {len(new)} URLs (gesamt: {len(urls)})")
            if not found:
                break
            time.sleep(0.6)
        except Exception as ex:
            print(f"  [list p{p_num}] Fehler: {ex}")
            break
    return list(urls)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run():
    db = load_db()
    existing_ids = {e["source_id"] for e in db if "source_id" in e}
    print(f"[db] {len(db)} Einträge geladen | 1stDibs: {sum(1 for e in db if e.get('source') == '1stdibs')}")

    total_new = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="en-US",
        )
        page = context.new_page()

        # Initial Cookie
        page.goto("https://www.1stdibs.com", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        try:
            page.click("#onetrust-accept-btn-handler", timeout=4000)
            print("[setup] Cookie-Banner akzeptiert")
        except:
            pass

        for gem_cat, list_url in STONE_URLS.items():
            print(f"\n=== {gem_cat.upper()} ===")
            product_urls = collect_product_urls(page, list_url, MAX_PAGES)

            new_count = skip_count = 0

            for i, url in enumerate(product_urls):
                id_match = re.search(r'id-(j_\w+)', url)
                source_id = f"1stdibs_{id_match.group(1)}" if id_match else None

                if source_id in existing_ids:
                    skip_count += 1
                    continue

                try:
                    print(f"  [{i+1}/{len(product_urls)}] Scraping {url.split('/')[-1]}")
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2200)

                    entry = parse_detail_page(page, url, gem_cat)
                    if entry:
                        db.append(entry)
                        existing_ids.add(entry["source_id"])
                        new_count += 1
                        total_new += 1

                    time.sleep(0.4)

                except Exception as ex:
                    print(f"  Fehler bei {url}: {ex}")

            print(f"  → Neu: {new_count} | Skip: {skip_count}")
            save_db(db)

        browser.close()

    print(f"\n✅ 1stDibs fertig — {total_new} neue Einträge")
    print(f"   DB gesamt: {len(db)}")

    # Pipeline
    print("\n[pipeline] Starte recategorize.py ...")
    subprocess.run(["python", "recategorize.py"], check=True)
    print("[pipeline] Starte aggregator.py ...")
    subprocess.run(["python", "aggregator.py"], check=True)
    print("\n✅ Pipeline abgeschlossen.")


if __name__ == "__main__":
    run()
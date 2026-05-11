"""
1stdibs_crawler.py — Retail-Preise von 1stDibs (v2)

Änderungen gegenüber v1:
- Full-Reset entfernt → inkrementelles Skip via existing_ids
- MAX_PAGES: 5 → 20
- Am Ende: recategorize.py → aggregator.py automatisch aufgerufen
"""

import re
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

from db import load_db, save_db
from categorizer import categorize

EUR_TO_USD = 1.08

# ---------------------------------------------------------------------------
# Stone URLs
# Untertypen (Rubellite, Rhodolite etc.) haben keine eigenen 1stDibs-URLs.
# tourmaline (20 Seiten) und garnet (20 Seiten) liefern diese Einträge —
# categorize() erkennt die Untertypen automatisch aus Titel/Beschreibung.
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
# Parse-Helfer
# ---------------------------------------------------------------------------

def get_price_from_page(page) -> float | None:
    try:
        text = page.locator('[data-tn="price-amount"]').first.inner_text(timeout=4000)
        is_eur = '€' in text
        clean = float(re.sub(r'[^\d.]', '', text.replace(',', '')))
        return round(clean * EUR_TO_USD, 2) if is_eur else clean
    except Exception:
        return None

def title_from_url(url: str) -> str:
    match = re.search(r'/loose-gemstones/([^/]+)/id-j_', url)
    if match:
        return match.group(1).replace('-', ' ').title()
    return ""

def parse_weight(text: str) -> float | None:
    match = re.search(r'Weight:\s*([\d.,]+)\s*Carat', text, re.IGNORECASE)
    if not match:
        match = re.search(r'([\d.,]+)\s*ct\b', text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1).replace(',', '.'))
    except Exception:
        return None

def parse_origin(text: str) -> str | None:
    origins = [
        "Sri Lanka", "Sri-Lanka", "Ceylon", "Burma", "Myanmar", "Colombia",
        "Brazil", "Tanzania", "Madagascar", "Mozambique", "Afghanistan",
        "Russia", "Thailand", "Vietnam", "Kenya", "Cambodia",
        "Kashmir", "Australia", "Zambia", "Zimbabwe", "Pakistan",
    ]
    for o in origins:
        if o.lower() in text.lower():
            return "Sri Lanka" if o in ("Sri-Lanka", "Ceylon") else o
    return None

def parse_treatment(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["no heat", "unheated", "untreated", "no treatment", "none"]):
        return "unheated"
    if any(k in t for k in ["heat", "enhancement", "heated", "beryllium", "glass"]):
        return "heated"
    return "unknown"

def parse_clarity(text: str) -> str | None:
    clarity_map = {
        "vvs":        "VVS",
        " vs ":       "VS",
        "vs,":        "VS",
        "si1":        "SI1",
        "si2":        "SI2",
        " si ":       "SI1",
        "eye clean":  "SI1",
        "loupe clean":"VVS",
        "eye-clean":  "SI1",
        "loupe-clean":"VVS",
        "flawless":   "VVS",
    }
    t = text.lower()
    for k, v in clarity_map.items():
        if k in t:
            return v
    return None


# ---------------------------------------------------------------------------
# Detail-Page Parser
# ---------------------------------------------------------------------------

def parse_detail_page(page, url: str, gem_category: str) -> dict | None:
    html = page.content()
    meta_match = re.search(r'Weight:.*?(?=<)', html, re.IGNORECASE | re.DOTALL)
    full_text = re.sub(r'<[^>]+>', ' ', html)

    carat = parse_weight(full_text)
    if not carat:
        return None

    price = get_price_from_page(page)
    if not price:
        return None

    id_match = re.search(r'id-(j_\w+)', url)
    source_id = f"1stdibs_{id_match.group(1)}" if id_match else None

    return {
        "source_id":   source_id,
        "source":      "1stdibs",
        "price_type":  "retail",
        "name_raw":    title_from_url(url),
        "gem_category": gem_category,
        "category":    None,
        "carat":       carat,
        "clarity":     parse_clarity(full_text),
        "treatment":   parse_treatment(full_text),
        "origin":      parse_origin(full_text),
        "colours":     [],
        "price_usd":   price,
        "currency_raw": "USD",
        "image_url":   None,
        "lot_url":     url,
        "crawled_at":  datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# URL-Collection (Listing-Seiten)
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
            time.sleep(0.5)
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
    print(f"[db] {len(db)} bestehende Einträge geladen")
    print(f"[db] {sum(1 for e in db if e.get('source') == '1stdibs')} davon 1stDibs")

    total_new = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()

        page.goto("https://www.1stdibs.com", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        try:
            page.click("#onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(1000)
            print("[setup] Cookie-Banner akzeptiert")
        except Exception:
            print("[setup] Kein Cookie-Banner")

        for gem_cat, list_url in STONE_URLS.items():
            print(f"\n=== {gem_cat.upper()} ===")
            product_urls = collect_product_urls(page, list_url, MAX_PAGES)
            print(f"  Gesamt URLs: {len(product_urls)}")

            new_count = skip_count = fail_count = 0

            for i, url in enumerate(product_urls):
                id_match = re.search(r'id-(j_\w+)', url)
                source_id = f"1stdibs_{id_match.group(1)}" if id_match else None

                if source_id and source_id in existing_ids:
                    skip_count += 1
                    continue

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2500)

                    entry = parse_detail_page(page, url, gem_cat)
                    if entry:
                        entry = categorize(entry)
                        db.append(entry)
                        existing_ids.add(entry["source_id"])
                        new_count += 1
                        total_new += 1
                    else:
                        fail_count += 1

                    time.sleep(0.3)

                except Exception as ex:
                    fail_count += 1
                    print(f"  [{i}] Fehler: {ex}")

            print(f"  Neu: {new_count} | Skip: {skip_count} | Fail: {fail_count}")
            save_db(db)

        browser.close()

    print(f"\n✅ 1stDibs fertig — {total_new} neue Einträge")
    print(f"   DB gesamt: {len(db)}")

    # Post-Processing Pipeline
    print("\n[pipeline] Starte recategorize.py ...")
    import subprocess
    subprocess.run(["python", "recategorize.py"], check=True)

    print("[pipeline] Starte aggregator.py ...")
    subprocess.run(["python", "aggregator.py"], check=True)

    print("\n✅ Pipeline abgeschlossen.")


if __name__ == "__main__":
    run()

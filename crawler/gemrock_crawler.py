"""
gemrock_crawler.py — GemRock Consolidated Crawler v4

Crawlt Listing-Seiten + Detailseiten in einem Durchlauf.
Kein enrich_clarity.py mehr nötig.

Modi:
  --mode update      (default) Überschreibt Einträge mit clarity=None
  --mode incremental Überspringt bereits vorhandene source_ids komplett

Optionen:
  --max-pages INT    Max. Seiten pro Steintyp (default: 10)
  --batch INT        Stoppt nach N neuen Einträgen gesamt (default: 0 = kein Limit)
  --no-catalogue     Katalog überspringen
  --no-reserve-off   No-Reserve Auktionen überspringen

Beispiele:
  python gemrock_crawler.py --mode update --max-pages 10
  python gemrock_crawler.py --mode incremental --max-pages 200 --batch 5000
"""

import re
import time
import subprocess
import argparse
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from config import (
    GEMROCK_GEMS, GEMROCK_CATALOGUE, GEMROCK_NORESERVE,
    REQUEST_DELAY, DETAIL_REQUEST_DELAY
)
from parser import parse_gemrock_lot
from categorizer import categorize
from db import load_db, save_db


# ---------------------------------------------------------------------------
# Cookie-Handling
# ---------------------------------------------------------------------------

def accept_cookies(page):
    try:
        btn = page.wait_for_selector(
            "#CybotCookiebotDialogBodyButtonAccept, "
            "[id*='accept'], [class*='accept-all'], "
            "button:has-text('Accept'), button:has-text('Akzeptieren')",
            timeout=5000
        )
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
            print("[crawler] Cookies akzeptiert")
    except PlaywrightTimeout:
        pass


# ---------------------------------------------------------------------------
# Clarity-Extraktion von der GemRock Detailseite
# ---------------------------------------------------------------------------

CLARITY_MAP = {
    "eye clean":         "SI1",
    "eyeclean":          "SI1",
    "eye-clean":         "SI1",
    "loupe clean":       "VVS",
    "loupe-clean":       "VVS",
    "flawless":          "VVS",
    "vvs":               "VVS",
    " vs ":              "VS",
    "si1":               "SI1",
    "si2":               "SI2",
    " i1 ":              "I1",
    "slightly included": "SI2",
    "heavily included":  "I1",
}

def _parse_clarity_from_text(text: str) -> str | None:
    t = text.lower()
    for keyword, grade in CLARITY_MAP.items():
        if keyword in t:
            return grade
    return None

def fetch_clarity_from_detail(page, lot_url: str) -> str | None:
    """
    Öffnet die GemRock Detailseite und extrahiert Clarity.
    Versucht drei HTML-Formate. Gibt None zurück wenn nicht gefunden.
    """
    if not lot_url:
        return None
    try:
        full_url = lot_url if lot_url.startswith("http") else f"https://www.gemrockauctions.com{lot_url}"
        page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1500)
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # Format A: <tr> mit Label "Clarity" + Wert in Nachbarzelle
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            for i, cell in enumerate(cells):
                if "clarity" in cell.get_text(strip=True).lower():
                    if i + 1 < len(cells):
                        clarity = _parse_clarity_from_text(cells[i + 1].get_text(" ", strip=True))
                        if clarity:
                            return clarity

        # Format B: <dt>Clarity</dt><dd>...</dd>
        for dt in soup.find_all("dt"):
            if "clarity" in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    clarity = _parse_clarity_from_text(dd.get_text(" ", strip=True))
                    if clarity:
                        return clarity

        # Format C: Freitext-Fallback
        return _parse_clarity_from_text(soup.get_text(" "))

    except Exception as ex:
        print(f"    [detail] Fehler bei {lot_url}: {ex}")
        return None


# ---------------------------------------------------------------------------
# Listing-Seite scrapen
# ---------------------------------------------------------------------------

def wait_for_items(page) -> bool:
    try:
        page.wait_for_selector(".ais-Hits-item", timeout=15000)
        return True
    except PlaywrightTimeout:
        return False

def scrape_listing_page(page, gem_category: str) -> list:
    soup = BeautifulSoup(page.content(), "lxml")
    items = soup.select(".ais-Hits-item")
    print(f"  [listing] {len(items)} .ais-Hits-item gefunden")
    results = []
    for item in items:
        parsed = parse_gemrock_lot(item, gem_category)
        if parsed:
            parsed["crawled_at"] = datetime.now(timezone.utc).isoformat()
            results.append(categorize(parsed))
    return results

def go_to_next_page(page) -> bool:
    try:
        next_btn = page.query_selector(
            ".ais-Pagination-item--nextPage:not(.ais-Pagination-item--disabled) a"
        )
        if not next_btn:
            return False
        next_btn.click()
        page.wait_for_timeout(2000)
        wait_for_items(page)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Haupt-Crawl-Funktion
# ---------------------------------------------------------------------------

def crawl_url(
    listing_page,
    detail_page,
    url: str,
    gem_category: str,
    existing_db: dict,
    mode: str = "update",
    max_pages: int = 10,
    price_type: str = "retail",
    batch_limit: int = 0,
    batch_counter: list = None,
) -> list:
    """
    batch_limit=0  -> kein Limit
    batch_limit=N  -> stoppt global nach N neuen Eintraegen
    batch_counter  -> [int] geteilter Zaehler ueber alle crawl_url Aufrufe
    """
    if batch_counter is None:
        batch_counter = [0]

    print(f"  [crawler] -> {url}")
    try:
        listing_page.goto(url, wait_until="networkidle", timeout=30000)
    except PlaywrightTimeout:
        print("  [crawler] Timeout beim Laden der Listing-Seite")
        return []

    accept_cookies(listing_page)

    if not wait_for_items(listing_page):
        print("  [crawler] Keine .ais-Hits-item — Seite leer oder unbekannter Slug")
        return []

    all_results = []

    for page_num in range(1, max_pages + 1):

        if batch_limit > 0 and batch_counter[0] >= batch_limit:
            print(f"  [batch] Limit von {batch_limit} erreicht — stoppe.")
            break

        lots = scrape_listing_page(listing_page, gem_category)
        print(f"  [crawler] Seite {page_num}: {len(lots)} Lots geparst")

        for lot in lots:

            if batch_limit > 0 and batch_counter[0] >= batch_limit:
                break

            lot["price_type"] = price_type
            sid = lot.get("source_id")

            if mode == "incremental" and sid in existing_db:
                continue

            if mode == "update" and sid in existing_db:
                existing = existing_db[sid]
                if existing.get("clarity") is not None:
                    continue
                print(f"    [detail] Clarity-Update fuer {sid}")
                clarity = fetch_clarity_from_detail(detail_page, lot.get("lot_url"))
                existing["clarity"] = clarity
                existing_db[sid] = existing
                time.sleep(DETAIL_REQUEST_DELAY)
                continue

            # Neuer Eintrag — Detailseite fuer Clarity aufrufen
            if lot.get("clarity") is None and lot.get("lot_url"):
                print(f"    [detail] Clarity fuer {sid}")
                clarity = fetch_clarity_from_detail(detail_page, lot.get("lot_url"))
                lot["clarity"] = clarity
                time.sleep(DETAIL_REQUEST_DELAY)

            all_results.append(lot)
            batch_counter[0] += 1

        if not go_to_next_page(listing_page):
            break
        time.sleep(REQUEST_DELAY)

    return all_results


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(
    mode: str = "update",
    max_pages: int = 10,
    batch_limit: int = 0,
    catalogue: bool = True,
    no_reserve: bool = True,
):
    db = load_db()
    existing_db = {e["source_id"]: e for e in db if "source_id" in e}
    print(f"[db] {len(db)} bestehende Eintraege geladen (mode={mode})")
    if batch_limit > 0:
        print(f"[batch] Limit: {batch_limit} neue Eintraege pro Lauf")

    total_new     = 0
    batch_counter = [0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
        )
        listing_page = context.new_page()
        detail_page  = context.new_page()

        listing_page.goto("https://www.gemrockauctions.com", wait_until="networkidle", timeout=20000)
        accept_cookies(listing_page)

        if catalogue:
            for gem in GEMROCK_GEMS:

                if batch_limit > 0 and batch_counter[0] >= batch_limit:
                    print(f"[batch] Gesamtlimit erreicht — ueberspringe restliche Gem-Typen.")
                    break

                print(f"\n=== Katalog: {gem.upper()} ===")
                url = GEMROCK_CATALOGUE.format(gem=gem, page=1)
                new_lots = crawl_url(
                    listing_page, detail_page, url, gem,
                    existing_db=existing_db,
                    mode=mode,
                    max_pages=max_pages,
                    price_type="retail",
                    batch_limit=batch_limit,
                    batch_counter=batch_counter,
                )
                for lot in new_lots:
                    existing_db[lot["source_id"]] = lot
                    total_new += 1
                print(f"  [db] {len(new_lots)} neue Eintraege fuer {gem}")
                time.sleep(REQUEST_DELAY * 2)

        if no_reserve and not (batch_limit > 0 and batch_counter[0] >= batch_limit):
            print("\n=== No-Reserve Auktionen (Wholesale) ===")
            url = GEMROCK_NORESERVE.format(page=1)
            new_lots = crawl_url(
                listing_page, detail_page, url, "mixed",
                existing_db=existing_db,
                mode=mode,
                max_pages=max_pages,
                price_type="wholesale",
                batch_limit=batch_limit,
                batch_counter=batch_counter,
            )
            for lot in new_lots:
                existing_db[lot["source_id"]] = lot
                total_new += 1
            print(f"  [db] {len(new_lots)} neue No-Reserve Eintraege")

        browser.close()

    final_db = list(existing_db.values())
    save_db(final_db)
    print(f"\n✅ GemRock fertig. Neu: {total_new} | DB gesamt: {len(final_db)}")

    print("\n[pipeline] Starte recategorize.py ...")
    subprocess.run(["python", "recategorize.py"], check=True)

    print("[pipeline] Starte aggregator.py ...")
    subprocess.run(["python", "aggregator.py"], check=True)

    print("\n✅ Pipeline abgeschlossen.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GemRock Consolidated Crawler v4")
    parser.add_argument(
        "--mode",
        choices=["update", "incremental"],
        default="update",
        help="update: Clarity-Update fuer bestehende | incremental: nur neue IDs"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Max. Seiten pro Steintyp (default: 10)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="Stoppt nach N neuen Eintraegen (0 = kein Limit)"
    )
    parser.add_argument("--no-catalogue",   action="store_true", help="Katalog ueberspringen")
    parser.add_argument("--no-reserve-off", action="store_true", help="No-Reserve ueberspringen")
    args = parser.parse_args()

    run(
        mode=args.mode,
        max_pages=args.max_pages,
        batch_limit=args.batch,
        catalogue=not args.no_catalogue,
        no_reserve=not args.no_reserve_off,
    )

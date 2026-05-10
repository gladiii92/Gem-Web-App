"""
GEMROCK CRAWLER v3 — Algolia InstantSearch (.ais-Hits-item)
Cookies werden automatisch akzeptiert.
"""
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from config import GEMROCK_GEMS, GEMROCK_CATALOGUE, GEMROCK_NORESERVE, REQUEST_DELAY
from parser import parse_gemrock_lot
from categorizer import categorize
from db import add_entries


def accept_cookies(page):
    """Akzeptiert CybotCookiebot falls vorhanden."""
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
        pass  # Kein Cookie-Dialog — weitermachen


def wait_for_items(page) -> bool:
    """Wartet bis .ais-Hits-item geladen sind. Gibt False bei Timeout zurück."""
    try:
        page.wait_for_selector(".ais-Hits-item", timeout=15000)
        return True
    except PlaywrightTimeout:
        return False


def scrape_page(page, gem_category: str) -> list:
    """Extrahiert alle .ais-Hits-item Elemente der aktuellen Seite."""
    soup  = BeautifulSoup(page.content(), "lxml")
    items = soup.select(".ais-Hits-item")
    print(f"[parser] {len(items)} .ais-Hits-item gefunden")

    results = []
    for item in items:
        parsed = parse_gemrock_lot(item, gem_category)
        if parsed:
            parsed["crawled_at"] = datetime.now(timezone.utc).isoformat()
            results.append(categorize(parsed))
    return results


def go_to_next_page(page) -> bool:
    """Klickt auf nächste Seite. Gibt False zurück wenn keine existiert."""
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


def crawl_url(page, url: str, gem_category: str,
              max_pages: int = 5, price_type: str = "retail") -> list:
    """Crawlt eine URL durch alle Seiten."""
    print(f"[crawler] → {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except PlaywrightTimeout:
        print("[crawler] Timeout beim Laden")
        return []

    accept_cookies(page)

    if not wait_for_items(page):
        print("[crawler] Keine .ais-Hits-item gefunden — Seite leer oder blockiert")
        return []

    all_results = []
    for page_num in range(1, max_pages + 1):
        lots = scrape_page(page, gem_category)
        for lot in lots:
            lot["price_type"] = price_type
        print(f"[crawler] Seite {page_num}: {len(lots)} Lots geparst")
        all_results.extend(lots)

        if not go_to_next_page(page):
            break
        time.sleep(REQUEST_DELAY)

    return all_results


def run(catalogue: bool = True, no_reserve: bool = True, max_pages: int = 3):
    total_new = 0

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
        page = context.new_page()

        # Einmalig Cookies akzeptieren durch erste Seite
        page.goto("https://www.gemrockauctions.com", wait_until="networkidle", timeout=20000)
        accept_cookies(page)

        if catalogue:
            for gem in GEMROCK_GEMS:
                print(f"\n=== Katalog: {gem.upper()} ===")
                url     = GEMROCK_CATALOGUE.format(gem=gem, page=1)
                results = crawl_url(page, url, gem, max_pages, price_type="retail")
                added   = add_entries(results)
                print(f"[db] {added} neue Einträge für {gem}")
                total_new += added
                time.sleep(REQUEST_DELAY * 2)

        if no_reserve:
            print("\n=== No-Reserve Auktionen (Wholesale) ===")
            url     = GEMROCK_NORESERVE.format(page=1)
            results = crawl_url(page, url, "mixed", max_pages, price_type="wholesale")
            added   = add_entries(results)
            print(f"[db] {added} neue No-Reserve Einträge")
            total_new += added

        browser.close()

    print(f"\n✅ Fertig. {total_new} neue Einträge gesamt.")


if __name__ == "__main__":
    run(catalogue=True, no_reserve=True, max_pages=3)

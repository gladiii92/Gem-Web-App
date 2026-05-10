"""
GEMROCK CRAWLER
Crawlt GemRock Auctions Katalog-Seiten für Retail-Preise.
Läuft lokal, respektiert robots.txt, verwendet Request-Delays.
"""
import time
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from config import (
    GEMROCK_GEMS, GEMROCK_CATALOGUE, GEMROCK_NORESERVE,
    REQUEST_DELAY, GEMROCK_BASE
)
from parser import parse_gemrock_lot
from categorizer import categorize
from db import add_entries


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_page(url: str) -> BeautifulSoup | None:
    """Lädt eine Seite und gibt BeautifulSoup zurück. None bei Fehler."""
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        print(f"[crawler] HTTP {resp.status_code} → {url}")
        return None
    except Exception as e:
        print(f"[crawler] Fehler beim Laden: {e}")
        return None


def has_next_page(soup: BeautifulSoup) -> bool:
    """Prüft ob eine weitere Seite existiert."""
    next_btn = soup.select_one("a[rel='next'], .pagination .next:not(.disabled)")
    return next_btn is not None


def scrape_lots(soup: BeautifulSoup, gem_category: str) -> list:
    """Extrahiert alle Lots von einer Seite."""
    # GemRock verwendet verschiedene Container-Klassen — wir probieren alle
    containers = soup.select(
        ".lot-item, .auction-item, .product-item, "
        "[class*='lot'], [class*='auction-lot']"
    )
    results = []
    for item in containers:
        parsed = parse_gemrock_lot(item, gem_category)
        if parsed:
            parsed["crawled_at"] = datetime.now(timezone.utc).isoformat()
            categorized = categorize(parsed)
            results.append(categorized)
    return results


def crawl_catalogue(gem: str, max_pages: int = 5) -> list:
    """Crawlt Katalog-Seiten für einen Steintyp."""
    all_results = []
    for page in range(1, max_pages + 1):
        url = GEMROCK_CATALOGUE.format(gem=gem, page=page)
        print(f"[crawler] Lade: {url}")
        soup = fetch_page(url)
        if not soup:
            break
        lots = scrape_lots(soup, gem)
        print(f"[crawler] Seite {page}: {len(lots)} Lots gefunden")
        all_results.extend(lots)
        if not has_next_page(soup):
            break
        time.sleep(REQUEST_DELAY)
    return all_results


def crawl_no_reserve(max_pages: int = 10) -> list:
    """Crawlt No-Reserve Auktionen (Wholesale-Preise)."""
    all_results = []
    for page in range(1, max_pages + 1):
        url = GEMROCK_NORESERVE.format(page=page)
        print(f"[crawler] No-Reserve Seite {page}: {url}")
        soup = fetch_page(url)
        if not soup:
            break
        lots = scrape_lots(soup, "mixed")
        # No-Reserve = Händlerpreise → price_type überschreiben
        for lot in lots:
            lot["price_type"] = "wholesale"
        print(f"[crawler] Seite {page}: {len(lots)} Lots gefunden")
        all_results.extend(lots)
        if not has_next_page(soup):
            break
        time.sleep(REQUEST_DELAY)
    return all_results


def run(catalogue: bool = True, no_reserve: bool = True, max_pages: int = 5):
    """Hauptfunktion — startet alle Crawler."""
    total_new = 0

    if catalogue:
        for gem in GEMROCK_GEMS:
            print(f"\n=== Katalog: {gem.upper()} ===")
            results = crawl_catalogue(gem, max_pages=max_pages)
            added = add_entries(results)
            print(f"[db] {added} neue Einträge für {gem}")
            total_new += added
            time.sleep(REQUEST_DELAY * 2)  # Extra Pause zwischen Kategorien

    if no_reserve:
        print("\n=== No-Reserve Auktionen (Wholesale) ===")
        results = crawl_no_reserve(max_pages=max_pages)
        added = add_entries(results)
        print(f"[db] {added} neue No-Reserve Einträge")
        total_new += added

    print(f"\n✅ Fertig. {total_new} neue Einträge gesamt.")


if __name__ == "__main__":
    run(catalogue=True, no_reserve=True, max_pages=3)

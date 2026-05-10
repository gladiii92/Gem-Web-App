"""
PARSER — extrahiert strukturierte Felder aus GemRock HTML-Elementen.
Gibt None zurück wenn ein Pflichtfeld fehlt.
"""
import re
from config import EUR_TO_USD


def parse_price(price_str: str, currency: str = "USD") -> float | None:
    """Bereinigt Preisstring und konvertiert zu USD."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.,]", "", price_str).replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if currency == "EUR":
        value = round(value * EUR_TO_USD, 2)
    return value


def parse_carat(text: str) -> float | None:
    """Extrahiert Karatwert aus Text wie '2.35ct' oder '2.35 Carats'."""
    match = re.search(r"(\d+\.?\d*)\s*(?:ct|carat|carats)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def parse_treatment(text: str) -> str:
    """Erkennt Behandlung: unheated / heated / unknown."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["unheated", "untreated", "no heat", "not heated", "natural"]):
        return "unheated"
    if any(k in text_lower for k in ["heated", "heat treated", "heat treatment"]):
        return "heated"
    return "unknown"


def parse_clarity(text: str) -> str | None:
    """Erkennt Clarity-Grade aus Beschreibungstext."""
    clarity_map = {
        "eye clean": "SI1",
        "eyeclean": "SI1",
        "eye-clean": "SI1",
        "vvs":  "VVS",
        "vs":   "VS",
        "si1":  "SI1",
        "si2":  "SI2",
        "i1":   "I1",
        "loupe clean": "VVS",
        "flawless": "VVS",
        "slightly included": "SI2",
        "heavily included": "I1",
    }
    text_lower = text.lower()
    for keyword, grade in clarity_map.items():
        if keyword in text_lower:
            return grade
    return None


def parse_origin(text: str) -> str | None:
    """Erkennt Herkunft aus Beschreibung."""
    origins = [
        "Sri Lanka", "Burma", "Myanmar", "Colombia", "Brazil", "Tanzania",
        "Madagascar", "Mozambique", "Afghanistan", "Russia", "Thailand",
        "Vietnam", "Kenya", "Nigeria", "Cambodia", "Kashmir"
    ]
    for origin in origins:
        if origin.lower() in text.lower():
            return origin
    return None


def parse_gemrock_lot(item_html, gem_category: str) -> dict | None:
    """
    Parst ein einzelnes GemRock Lot-Element.
    Gibt None zurück wenn Pflichtfelder (Preis, Karat) fehlen.
    """
    from bs4 import BeautifulSoup

    if isinstance(item_html, str):
        soup = BeautifulSoup(item_html, "lxml")
    else:
        soup = item_html

    # Titel / Beschreibung
    title_el = soup.select_one(".lot-title, h3, .auction-title, [class*='title']")
    title = title_el.get_text(strip=True) if title_el else ""

    # Preis
    price_el = soup.select_one(".price, .lot-price, [class*='price']")
    price_raw = price_el.get_text(strip=True) if price_el else ""
    currency = "EUR" if "€" in price_raw else "USD"
    price_usd = parse_price(price_raw, currency)
    if not price_usd:
        return None

    # Karat — erst aus dediziertem Feld, dann aus Titel
    carat_el = soup.select_one("[class*='carat'], [class*='weight']")
    carat_raw = carat_el.get_text(strip=True) if carat_el else title
    carat = parse_carat(carat_raw)
    if not carat:
        return None

    # Bild
    img_el = soup.select_one("img[src]")
    image_url = img_el["src"] if img_el else None

    # Lot-ID aus Link
    link_el = soup.select_one("a[href*='/auctions/']")
    lot_url = link_el["href"] if link_el else ""
    lot_id = re.search(r"/auctions/(\d+)", lot_url)
    source_id = f"gemrock_{lot_id.group(1)}" if lot_id else f"gemrock_{hash(title + str(price_usd))}"

    full_text = title + " " + (soup.get_text(separator=" "))

    return {
        "source_id":    source_id,
        "source":       "gemrock",
        "price_type":   "retail",        # GemRock Katalog = Retailpreise
        "name_raw":     title,
        "gem_category": gem_category,    # z.B. "sapphire"
        "category":     None,            # wird von categorizer.py gesetzt
        "carat":        carat,
        "clarity":      parse_clarity(full_text),
        "treatment":    parse_treatment(full_text),
        "origin":       parse_origin(full_text),
        "price_usd":    price_usd,
        "currency_raw": currency,
        "image_url":    image_url,
        "lot_url":      GEMROCK_BASE + lot_url if lot_url.startswith("/") else lot_url,
        "crawled_at":   None,            # wird von crawler gesetzt
    }


try:
    from config import GEMROCK_BASE
except ImportError:
    GEMROCK_BASE = "https://www.gemrockauctions.com"

"""
PARSER v4 — GemRock speichert alle Daten als JSON im x-data Attribut.
Kein fragiles HTML-Parsing mehr — direkt aus dem Datenstrom.

Änderungen v4:
- Laufende Auktionen (status="open") werden gefiltert — nur closed + catalogue
"""
import re
import json
import html as html_module
from config import EUR_TO_USD

def extract_auction_json(item_soup) -> dict | None:
    """
    Extrahiert das auction-JSON aus dem x-data Attribut des .ais-Hits-item.
    Format: x-data="{ auction: {...}, ... }"
    """
    outer_div = item_soup.find("div", attrs={"x-data": True})
    if not outer_div:
        return None

    x_data_raw = outer_div.get("x-data", "")
    x_data_decoded = html_module.unescape(x_data_raw)

    match = re.search(r'auction:\s*(\{.*?\}),\s*\n\s*init', x_data_decoded, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

def parse_treatment_from_variants(variants: list) -> str:
    """Liest Treatment direkt aus variants-Array."""
    all_values = " ".join(
        str(v) for item in variants for v in item.values()
    ).lower()
    if any(k in all_values for k in ["no treatment", "unheated", "untreated", "natural"]):
        return "unheated"
    if any(k in all_values for k in ["heated", "heat", "beryllium", "glass"]):
        return "heated"
    return "unknown"

def parse_clarity(text: str) -> str | None:
    clarity_map = {
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
    t = text.lower()
    for keyword, grade in clarity_map.items():
        if keyword in t:
            return grade
    return None

def parse_origin(text: str) -> str | None:
    origins = [
        "Sri Lanka", "Ceylon", "Burma", "Myanmar", "Colombia", "Brazil",
        "Tanzania", "Madagascar", "Mozambique", "Afghanistan", "Russia",
        "Thailand", "Vietnam", "Kenya", "Nigeria", "Cambodia", "Kashmir",
        "Australia", "Zambia", "Zimbabwe", "Pakistan", "Nigeria"
    ]
    for origin in origins:
        if origin.lower() in text.lower():
            return "Sri Lanka" if origin == "Ceylon" else origin
    return None

def parse_colours(colours: list) -> str:
    return ", ".join(colours) if colours else ""

def parse_gemrock_lot(item_soup, gem_category: str) -> dict | None:
    """
    Parst ein .ais-Hits-item durch direktes JSON-Parsing aus x-data.
    Gibt None zurück wenn:
      - Pflichtfelder fehlen (price, weight)
      - Laufende Auktion (type=auction, status=open) — Startgebote sind kein Marktwert
    """
    auction = extract_auction_json(item_soup)
    if not auction:
        return None

    # Laufende Auktionen ausfiltern — nur abgeschlossene Auktionen + Catalogue
    if auction.get("type") == "auction" and auction.get("status") == "open":
        return None

    price  = auction.get("price")
    weight = auction.get("weight")

    if not price or not weight or price <= 0 or weight <= 0:
        return None

    title    = auction.get("title", "")
    variants = auction.get("variants", [])
    colours  = auction.get("colours", [])
    full_text = title + " " + parse_colours(colours)

    return {
        "source_id":    f"gemrock_{auction['id']}",
        "source":       "gemrock",
        "price_type":   "retail" if auction.get("type") == "catalogue" else "wholesale",
        "name_raw":     title,
        "gem_category": gem_category,
        "category":     None,
        "carat":        float(weight),
        "clarity":      parse_clarity(full_text),
        "treatment":    parse_treatment_from_variants(variants),
        "origin":       parse_origin(full_text),
        "colours":      colours,
        "price_usd":    float(price),
        "currency_raw": "USD",
        "image_url":    auction.get("image"),
        "lot_url":      auction.get("url"),
        "crawled_at":   None,
        # Zusätzliche Felder für Qualitätskontrolle
        "auction_status": auction.get("status"),   # "closed" | "catalogue" | None
        "num_bids":       auction.get("num_bids"),  # Anzahl Gebote — Qualitätsindikator
        "ends_at":        auction.get("ends_at"),   # Endzeitpunkt der Auktion
    }

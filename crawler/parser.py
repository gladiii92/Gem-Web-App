"""
PARSER v5 — GemRock speichert alle Daten als JSON im x-data Attribut.
Kein fragiles HTML-Parsing mehr — direkt aus dem Datenstrom.
"""
import re
import json
import html as html_module
from config import EUR_TO_USD

def extract_auction_json(item_soup) -> dict | None:
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
    all_values = " ".join(str(v) for item in variants for v in item.values()).lower()
    if any(k in all_values for k in ["no treatment", "unheated", "untreated", "natural"]):
        return "unheated"
    if any(k in all_values for k in ["heated", "heat", "beryllium", "glass"]):
        return "heated"
    return "unknown"

def parse_clarity(text: str) -> str | None:
    if not text:
        return None

    t = text.lower()

    if "flawless" in t:
        return "VVS"
    if "loupe clean" in t:
        return "VVS"
    if "eye clean" in t or "eyeclean" in t or "eye-clean" in t:
        return "SI1"

    clarity_map = [
        (r"\bvvs\b", "VVS"),
        (r"\bvs1\b", "VS"),
        (r"\bvs2\b", "VS"),
        (r"\bvs\b", "VS"),
        (r"\bsi1\b", "SI1"),
        (r"\bsi2\b", "SI2"),
        (r"\bsi\b", "SI1"),
        (r"\bi1\b", "I1"),
        (r"\bi\b", "I1"),
        (r"\bslightly included\b", "SI2"),
        (r"\bheavily included\b", "I1"),
    ]

    for pattern, grade in clarity_map:
        if re.search(pattern, t):
            return grade

    return None

def parse_origin(text: str) -> str | None:
    origins = [
        "Sri Lanka", "Ceylon", "Burma", "Myanmar", "Colombia", "Brazil",
        "Tanzania", "Madagascar", "Mozambique", "Afghanistan", "Russia",
        "Thailand", "Vietnam", "Kenya", "Nigeria", "Cambodia", "Kashmir",
        "Australia", "Zambia", "Zimbabwe", "Pakistan"
    ]
    for origin in origins:
        if origin.lower() in text.lower():
            return "Sri Lanka" if origin == "Ceylon" else origin
    return None

def parse_colours(colours: list) -> str:
    return ", ".join(colours) if colours else ""

def parse_gemrock_lot(item_soup, gem_category: str) -> dict | None:
    auction = extract_auction_json(item_soup)
    if not auction:
        return None

    if auction.get("type") == "auction" and auction.get("status") == "open":
        return None

    price = auction.get("price")
    weight = auction.get("weight")

    if not price or not weight or price <= 0 or weight <= 0:
        return None

    title = auction.get("title", "")
    variants = auction.get("variants", [])
    colours = auction.get("colours", [])
    full_text = " ".join([
        title,
        parse_colours(colours),
        " ".join(str(v) for item in variants for v in item.values()),
    ])

    return {
        "source_id": f"gemrock_{auction['id']}",
        "source": "gemrock",
        "price_type": "retail" if auction.get("type") == "catalogue" else "wholesale",
        "name_raw": title,
        "gem_category": gem_category,
        "category": None,
        "carat": float(weight),
        "clarity": parse_clarity(full_text),
        "treatment": parse_treatment_from_variants(variants),
        "origin": parse_origin(full_text),
        "colours": colours,
        "price_usd": float(price),
        "currency_raw": "USD",
        "image_url": auction.get("image"),
        "lot_url": auction.get("url"),
        "crawled_at": None,
        "auction_status": auction.get("status"),
        "num_bids": auction.get("num_bids"),
        "ends_at": auction.get("ends_at"),
    }
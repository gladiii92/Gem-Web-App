"""
CATEGORIZER v2 — komplett englische Keywords für GemRock-Titel
Logik: gem_category (aus der URL) + Farb-/Herkunfts-Keywords aus name_raw
"""

COLOUR_BLUE   = ["blue", "royal blue", "cornflower", "teal", "steel blue"]
COLOUR_PINK   = ["pink", "rose", "magenta", "hot pink"]
COLOUR_GREEN  = ["green", "mint", "forest", "olive", "lime"]
COLOUR_YELLOW = ["yellow", "golden", "gold", "lemon", "honey", "sherry", "imperial"]
COLOUR_ORANGE = ["orange", "mandarin", "tangerine", "peach", "creamside", "cremesicle"]
COLOUR_PURPLE = ["purple", "violet", "lavender", "lilac"]
COLOUR_RED    = ["red", "crimson", "scarlet", "blood red"]
COLOUR_WHITE  = ["white", "colorless", "colourless", "clear"]
COLOUR_TEAL   = ["teal", "blue-green", "bluegreen", "blue green", "greenish blue", "bluish green"]


def _has_any(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _has_none(text: str, keywords: list) -> bool:
    t = text.lower()
    return not any(k in t for k in keywords)


def categorize(entry: dict) -> dict:
    gem  = entry.get("gem_category", "").lower()
    name = entry.get("name_raw", "").lower()
    cols = " ".join(entry.get("colours", []))
    text = name + " " + cols

    # ── Paraiba (sehr spezifisch — vor allgemeinem Tourmaline prüfen)
    if "paraiba" in text or "paraíba" in text:
        if _has_any(text, ["greenish", "green"]):
            return _set(entry, 26, "Paraiba Tourmaline (Greenish Blue)")
        return _set(entry, 27, "Paraiba Tourmaline (Bluish Green)")

    # ── Alexandrit
    if "alexandrite" in text or "alexandrit" in text:
        if _has_any(text, COLOUR_YELLOW + COLOUR_ORANGE):
            return _set(entry, 23, "Alexandrit (Yellow/Green - Red/Orange)")
        return _set(entry, 22, "Alexandrit (Blue/Green - Purple/Red)")

    # ── Padparadscha
    if "padparadscha" in text:
        return _set(entry, 24, "Padparadscha Saphir (Pink-Orange, Sri Lanka)")

    # ── Morganite (vor Rubin/Saphir — "rose" in COLOUR_PINK würde sonst matchen)
    if "morganite" in text:
        return _set(entry, 37, "Morganite (Pink/Peach)")

    # ── Rubin
    if gem == "ruby" or "ruby" in text or "rubin" in text:
        if _has_any(text, COLOUR_PURPLE + ["purplish", "reddish purple"]):
            return _set(entry, 19, "Rubin (Purplish Red / Reddish Purple)")
        return _set(entry, 21, "Rubin (Red, Sri Lanka)")

    # ── Saphir
    if gem == "sapphire" or "sapphire" in text or "saphir" in text:
        if "padparadscha" in text:
            return _set(entry, 24, "Padparadscha Saphir (Pink-Orange, Sri Lanka)")
        if _has_any(text, COLOUR_TEAL + ["blue-green", "teal"]):
            return _set(entry, 15, "Saphir (Grün/Teal, Sri Lanka)")
        if _has_any(text, COLOUR_PINK):
            return _set(entry, 17, "Saphir (Pink, Sri Lanka)")
        if _has_any(text, COLOUR_YELLOW):
            return _set(entry, 10, "Saphir (Gelb, Sri Lanka)")
        if _has_any(text, COLOUR_PURPLE):
            return _set(entry, 13, "Saphir (Purple, Sri Lanka)")
        if _has_any(text, COLOUR_WHITE):
            return _set(entry, 5, "Saphir (Weiß, Sri Lanka)")
        if _has_any(text, COLOUR_BLUE):
            return _set(entry, 25, "Saphir (Blau, Sri Lanka)")
        return _set(entry, 25, "Saphir (Blau, Sri Lanka)")

    # ── Smaragd
    if gem == "emerald" or "emerald" in text or "smaragd" in text:
        return _set(entry, 18, "Smaragd (Grün, Overall)")

    # ── Spinell
    if gem == "spinel" or "spinel" in text or "spinell" in text:
        if _has_any(text, COLOUR_ORANGE):
            return _set(entry, 16, "Spinell (Orange)")
        if _has_any(text, COLOUR_BLUE + COLOUR_PURPLE):
            return _set(entry, 14, "Spinell (Blau/Purple)")
        return _set(entry, 20, "Spinell (NormalRot & Jedi(Pink) & Kobaltblau)")

    # ── Tanzanit
    if gem == "tanzanite" or "tanzanite" in text or "tanzanit" in text:
        if _has_any(text, ["violetish", "violet", "bluish violet"]):
            return _set(entry, 7, "Tanzanit (Violetish Blue)")
        return _set(entry, 6, "Tanzanit (Bluish Violet)")

    # ── Topaz
    if gem == "topaz" or "topaz" in text:
        return _set(entry, 1, "Katlang Topaz (Imperial Orange/Pink)")

    # ── Tourmaline (Handelsnamen zuerst — dann unknown_tourmaline als Fallback)
    if gem == "tourmaline" or "tourmaline" in text or "tourmalin" in text:
        if "rubellite" in text:
            return _set(entry, 28, "Rubellite (Pink/Red)")
        if "indicolite" in text:
            return _set(entry, 29, "Indicolite (Blue/Blue-Green)")
        if "chrome" in text and _has_any(text, COLOUR_GREEN):
            return _set(entry, 30, "Chrome Tourmaline (Green)")
        if "watermelon" in text:
            return _set(entry, 31, "Watermelon Tourmaline (Pink/Green)")
        entry["category"] = "unknown_tourmaline"
        entry["category_id"] = None
        return entry

    # ── Rubellite ohne "tourmaline" im Titel (eigenständiger Handelsname)
    if "rubellite" in text:
        return _set(entry, 28, "Rubellite (Pink/Red)")

    # ── Granat/Garnet Untertypen
    if gem == "garnet" or "garnet" in text or "granat" in text:

        # Demantoid zuerst (spezifisch)
        if "demantoid" in text:
            if _has_any(text, ["yellow", "yellowish"]):
                return _set(entry, 12, "Demantoid Garnet/Granat (Yellowish Green)")
            return _set(entry, 9, "Demantoid Garnet/Granat (Green)")

        # Tsavorit
        if "tsavorite" in text or "tsavorit" in text:
            if _has_any(text, ["yellow", "yellowish"]):
                return _set(entry, 4, "Tsavorit Garnet/Granat (Yellowish Green)")
            return _set(entry, 11, "Tsavorit Garnet/Granat (Green)")

        # Color-Change (vor Malaya prüfen)
        if "color change" in text or "colour change" in text or "color-change" in text:
            return _set(entry, 34, "Color-Change Garnet")

        # Malaya
        if "malaya" in text:
            return _set(entry, 33, "Malaya Garnet (Orange/Pink)")

        # Grossular / Mandarin / Spessartite
        if any(k in text for k in ["grossular", "mandarin", "spessartite", "spessartine", "pyralspite"]):
            if _has_any(text, COLOUR_ORANGE):
                return _set(entry, 8, "Grossular Garnet/Granat (Mandarin/Orange)")
            if _has_any(text, ["yellow", "yellowish"]):
                return _set(entry, 3, "Grossular Garnet/Granat (Yellowish Green)")
            return _set(entry, 2, "Grossular Garnet/Granat (Green)")

        # Rhodolite / Pyrope / Almandine
        if "rhodolite" in text:
            return _set(entry, 32, "Rhodolite Garnet (Pink/Purple)")
        if "pyrope" in text:
            return _set(entry, 35, "Pyrope Garnet (Red)")
        if "almandine" in text or "almandite" in text:
            return _set(entry, 36, "Almandine Garnet (Deep Red)")

        # Allgemeiner Farb-Fallback
        if _has_any(text, COLOUR_GREEN):
            return _set(entry, 2, "Grossular Garnet/Granat (Green)")
        if _has_any(text, COLOUR_ORANGE):
            return _set(entry, 8, "Grossular Garnet/Granat (Mandarin/Orange)")

        entry["category"] = "unknown_garnet"
        entry["category_id"] = None
        return entry

    # ── Kein Match ──
    entry["category"] = "unknown"
    entry["category_id"] = None
    return entry


def _set(entry: dict, cat_id: int, cat_name: str) -> dict:
    entry["category"] = cat_name
    entry["category_id"] = cat_id
    return entry
"""
CATEGORIZER v2 — komplett englische Keywords für GemRock-Titel
Logik: gem_category (aus der URL) + Farb-/Herkunfts-Keywords aus name_raw
"""

# Struktur: (category_id, category_name, gem_types, must_colours, exclude_colours)
# gem_types: passt auf gem_category ODER auf Keywords im Titel
# must_colours: wenn gesetzt, muss mindestens eines im Titel stehen
# exclude_colours: wenn gesetzt, darf keines davon im Titel stehen

COLOUR_BLUE    = ["blue", "royal blue", "cornflower", "teal", "steel blue"]
COLOUR_PINK    = ["pink", "rose", "magenta", "hot pink"]
COLOUR_GREEN   = ["green", "mint", "forest", "olive", "lime"]
COLOUR_YELLOW  = ["yellow", "golden", "gold", "lemon", "honey", "sherry", "imperial"]
COLOUR_ORANGE  = ["orange", "mandarin", "tangerine", "peach", "creamside", "cremesicle"]
COLOUR_PURPLE  = ["purple", "violet", "lavender", "lilac"]
COLOUR_RED     = ["red", "crimson", "scarlet", "blood red"]
COLOUR_WHITE   = ["white", "colorless", "colourless", "clear"]
COLOUR_TEAL    = ["teal", "blue-green", "bluegreen", "blue green", "greenish blue", "bluish green"]


def _has_any(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _has_none(text: str, keywords: list) -> bool:
    t = text.lower()
    return not any(k in t for k in keywords)


def categorize(entry: dict) -> dict:
    """
    Ordnet Eintrag einer data.json Kategorie zu.
    Nutzt gem_category (aus URL-Slug) + name_raw + colours für Zuordnung.
    """
    gem   = entry.get("gem_category", "").lower()
    name  = entry.get("name_raw", "").lower()
    cols  = " ".join(entry.get("colours", []))
    text  = name + " " + cols  # kombinierter Such-Text

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
            return _set(entry, 5,  "Saphir (Weiß, Sri Lanka)")
        if _has_any(text, COLOUR_BLUE):
            return _set(entry, 25, "Saphir (Blau, Sri Lanka)")
        # Fallback ohne Farbe → Blau (häufigste Kategorie)
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
        # Rot / Pink / Jedi / Cobalt → alle unter NormalRot
        return _set(entry, 20, "Spinell (NormalRot & Jedi(Pink) & Kobaltblau)")

    # ── Tanzanit
    if gem == "tanzanite" or "tanzanite" in text or "tanzanit" in text:
        if _has_any(text, ["violetish", "violet", "bluish violet"]):
            return _set(entry, 7, "Tanzanit (Violetish Blue)")
        return _set(entry, 6, "Tanzanit (Bluish Violet)")

    # ── Topaz
    if gem == "topaz" or "topaz" in text:
        return _set(entry, 1, "Katlang Topaz (Imperial Orange/Pink)")

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

        # Grossular / Mandarin / Orange Garnet
        if any(k in text for k in ["grossular", "mandarin", "spessartite", "spessartine", "malaya", "pyralspite"]):
            if _has_any(text, COLOUR_ORANGE):
                return _set(entry, 8, "Grossular Garnet/Granat (Mandarin/Orange)")
            if _has_any(text, ["yellow", "yellowish"]):
                return _set(entry, 3, "Grossular Garnet/Granat (Yellowish Green)")
            return _set(entry, 2, "Grossular Garnet/Granat (Green)")

        # Rhodolite, Pyrope → Rot-lila → kein Match in data.json → unknown lassen
        if any(k in text for k in ["rhodolite", "pyrope", "almandine", "almandite"]):
            entry["category"] = "unknown_rhodolite"
            entry["category_id"] = None
            return entry

        # Allgemeiner grüner Granat
        if _has_any(text, COLOUR_GREEN):
            return _set(entry, 2, "Grossular Garnet/Granat (Green)")
        if _has_any(text, COLOUR_ORANGE):
            return _set(entry, 8, "Grossular Garnet/Granat (Mandarin/Orange)")

        entry["category"] = "unknown_garnet"
        entry["category_id"] = None
        return entry

    # ── Tourmaline (allgemein — nach Paraiba!)
    if gem == "tourmaline" or "tourmaline" in text or "tourmalin" in text:
        # Tourmaline nicht in data.json außer Paraiba → als unknown markieren
        entry["category"] = "unknown_tourmaline"
        entry["category_id"] = None
        return entry

    # ── Kein Match
    entry["category"]    = "unknown"
    entry["category_id"] = None
    return entry


def _set(entry: dict, cat_id: int, cat_name: str) -> dict:
    entry["category"]    = cat_name
    entry["category_id"] = cat_id
    return entry

"""
CATEGORIZER — ordnet einen gecrawlten Rohstein einer data.json-Kategorie zu.
Keyword-Matching auf name_raw + origin + treatment.
"""

# Mapping: data.json Kategorie-ID → Keywords die matchen müssen
# Format: (kategorie_name, [pflicht-keywords], [ausschluss-keywords])
CATEGORY_RULES = [
    # Paraiba zuerst — spezifischste Kategorie
    (27, "Paraiba Tourmaline (Bluish Green)",  ["paraiba", "tourmaline"], ["greenish"]),
    (26, "Paraiba Tourmaline (Greenish Blue)",  ["paraiba", "tourmaline", "greenish"], []),

    # Alexandrit
    (22, "Alexandrit (Blue/Green - Purple/Red)", ["alexandrite", "alexandrit"], ["yellow", "orange"]),
    (23, "Alexandrit (Yellow/Green - Red/Orange)", ["alexandrite", "alexandrit"], []),

    # Padparadscha
    (24, "Padparadscha Saphir (Pink-Orange, Sri Lanka)", ["padparadscha"], []),

    # Rubin
    (21, "Rubin (Red, Sri Lanka)", ["ruby", "rubin", "red"], ["purple", "purplish"]),
    (19, "Rubin (Purplish Red / Reddish Purple)", ["ruby", "rubin"], []),

    # Saphire — Farbe entscheidet
    (25, "Saphir (Blau, Sri Lanka)",      ["sapphire", "saphir", "blue"],   ["pink","yellow","green","purple","white","teal"]),
    (17, "Saphir (Pink, Sri Lanka)",      ["sapphire", "saphir", "pink"],   ["orange"]),
    (15, "Saphir (Grün/Teal, Sri Lanka)", ["sapphire", "saphir"],           ["blue","pink","yellow","purple","white"]),
    (13, "Saphir (Purple, Sri Lanka)",    ["sapphire", "saphir", "purple"], []),
    (10, "Saphir (Gelb, Sri Lanka)",      ["sapphire", "saphir", "yellow"], []),
    (5,  "Saphir (Weiß, Sri Lanka)",      ["sapphire", "saphir", "white"],  []),

    # Smaragd
    (18, "Smaragd (Grün, Overall)", ["emerald", "smaragd"], []),

    # Spinell
    (20, "Spinell (NormalRot & Jedi(Pink) & Kobaltblau)", ["spinel", "spinell", "red"],    ["orange","blue","purple"]),
    (14, "Spinell (Blau/Purple)",                         ["spinel", "spinell", "blue"],   ["red","orange"]),
    (16, "Spinell (Orange)",                              ["spinel", "spinell", "orange"],  []),

    # Demantoid
    (9,  "Demantoid Garnet/Granat (Green)",         ["demantoid", "green"],          ["yellow"]),
    (12, "Demantoid Garnet/Granat (Yellowish Green)",["demantoid"],                  []),

    # Tsavorit
    (11, "Tsavorit Garnet/Granat (Green)",          ["tsavorite", "tsavorit", "green"],   ["yellow"]),
    (4,  "Tsavorit Garnet/Granat (Yellowish Green)", ["tsavorite", "tsavorit"],             []),

    # Grossular
    (8,  "Grossular Garnet/Granat (Mandarin/Orange)", ["grossular", "garnet", "orange"],  []),
    (2,  "Grossular Garnet/Granat (Green)",           ["grossular", "garnet", "green"],   ["yellow","orange"]),
    (3,  "Grossular Garnet/Granat (Yellowish Green)", ["grossular", "garnet"],             []),

    # Tanzanit
    (7,  "Tanzanit (Violetish Blue)",  ["tanzanite", "tanzanit", "violet"], []),
    (6,  "Tanzanit (Bluish Violet)",   ["tanzanite", "tanzanit"],           []),

    # Topaz
    (1,  "Katlang Topaz (Imperial Orange/Pink)", ["topaz", "imperial"], []),
]


def categorize(entry: dict) -> dict:
    """
    Versucht dem Eintrag eine data.json-Kategorie zuzuweisen.
    Gibt den Eintrag mit gesetztem 'category' und 'category_id' zurück.
    Bei keinem Match: category = 'unknown'
    """
    text = " ".join([
        entry.get("name_raw", ""),
        entry.get("origin", "") or "",
        entry.get("gem_category", ""),
    ]).lower()

    for cat_id, cat_name, must_have, must_not in CATEGORY_RULES:
        if all(kw in text for kw in must_have):
            if not any(kw in text for kw in must_not):
                entry["category"]    = cat_name
                entry["category_id"] = cat_id
                return entry

    entry["category"]    = "unknown"
    entry["category_id"] = None
    return entry

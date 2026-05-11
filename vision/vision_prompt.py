"""
vision_prompt.py v6 — Hybrid RAG: Kategorie-Filter + Farb-Ranking
"""

import json
import random
from pathlib import Path

CRAWL_DB = Path(__file__).parent.parent / "crawler" / "crawl_db.json"

# Mapping: Modell-Output (Schlüsselwörter) → gem_category in crawl_db
STONE_TO_CATEGORY = {
    "sapphire":        "sapphire",
    "saphir":          "sapphire",
    "ruby":            "ruby",
    "rubin":           "ruby",
    "emerald":         "emerald",
    "smaragd":         "emerald",
    "tourmaline":      "tourmaline",
    "turmalin":        "tourmaline",
    "rubellite":       "tourmaline",
    "indicolite":      "tourmaline",
    "paraiba":         "tourmaline",
    "chrome tourmaline": "tourmaline",
    "watermelon":      "tourmaline",
    "spinel":          "spinel",
    "spinell":         "spinel",
    "tanzanite":       "tanzanite",
    "tansanit":        "tanzanite",
    "garnet":          "garnet",
    "granat":          "garnet",
    "tsavorite":       "garnet",
    "demantoid":       "garnet",
    "rhodolite":       "garnet",
    "malaya":          "garnet",
    "alexandrite":     "alexandrite",
    "alexandrit":      "alexandrite",
    "topaz":           "topaz",
    "topas":           "topaz",
}

# Farb-Keywords für Ranking innerhalb einer Kategorie
COLOR_KEYWORDS = {
    "blue":   ["blue", "blau", "cornflower", "royal", "ceylon", "teal"],
    "green":  ["green", "grün", "teal", "mint", "chrome", "tsavorite", "emerald"],
    "red":    ["red", "rot", "ruby", "rubin", "scarlet", "crimson"],
    "pink":   ["pink", "rosa", "padparadscha", "salmon", "hot pink"],
    "purple": ["purple", "violet", "violett", "lavender", "tanzanite"],
    "yellow": ["yellow", "gelb", "golden", "canary", "lemon"],
    "orange": ["orange", "padparadscha", "mandarin", "spessartine"],
    "white":  ["white", "weiß", "colorless", "farblos"],
    "black":  ["black", "schwarz"],
}


def load_db() -> list:
    if not CRAWL_DB.exists():
        return []
    with open(CRAWL_DB, encoding="utf-8") as f:
        return json.load(f)

CORRECTIONS_FILE = Path(__file__).parent / "corrections.json"

def build_correction_hint(max_entries: int = 5) -> str:
    """
    Liest corrections.json und baut einen gezielten Warn-Block.
    Häufigste Verwechslungen werden priorisiert (nach Anzahl sortiert).
    """
    if not CORRECTIONS_FILE.exists():
        return ""

    with open(CORRECTIONS_FILE, encoding="utf-8") as f:
        corrections = json.load(f)

    if not corrections:
        return ""

    # Verwechslungs-Paare zählen: "Ruby → Pink Sapphire" etc.
    from collections import Counter
    pairs = Counter(
        f"{c['predicted']} → {c['correct']}"
        for c in corrections
        if c.get("predicted") and c.get("correct")
    )

    if not pairs:
        return ""

    top = pairs.most_common(max_entries)
    lines = [f"  - Previously misidentified: {pair} ({count}x)" for pair, count in top]

    return (
        "LEARNED CORRECTIONS — these specific mistakes have occurred before, "
        "weight your analysis accordingly:\n" + "\n".join(lines)
    )

def _color_score(entry: dict, color_hint: str) -> int:
    """
    Gibt 0–3 zurück je nach Farbübereinstimmung.
    Höher = besser passend zum gesuchten Farbton.
    """
    if not color_hint:
        return 0

    keywords = COLOR_KEYWORDS.get(color_hint.lower(), [color_hint.lower()])
    score = 0

    # colours-Feld (explizit gepflegt) zählt doppelt
    for c in entry.get("colours", []):
        if any(k in c.lower() for k in keywords):
            score += 2

    # name_raw als Fallback (für Einträge mit leerem colours-Feld)
    name = entry.get("name_raw", "").lower()
    if any(k in name for k in keywords):
        score += 1

    return score


def get_rag_examples(
    db: list,
    gem_category: str | None = None,
    color_hint: str | None = None,
    n: int = 5,
) -> str:
    """
    Option C — Hybrid RAG:
    Stufe 1: Filter auf gem_category
    Stufe 2: Innerhalb der Kategorie nach Farbähnlichkeit sortieren
    Stufe 3: Top-n zurückgeben; bei zu wenig Treffern: Auffüllen aus Rest-DB
    """
    valid = [
        e for e in db
        if e.get("name_raw") and e.get("carat") and e.get("clarity") and e.get("price_usd")
    ]

    if not valid:
        return ""

    # Stufe 1 — Kategorie-Filter
    if gem_category:
        category_pool = [e for e in valid if e.get("gem_category") == gem_category]
    else:
        category_pool = valid

    # Fallback: wenn Kategorie zu wenig Einträge hat, Rest-DB auffüllen
    if len(category_pool) < n:
        remainder = [e for e in valid if e not in category_pool]
        category_pool = category_pool + random.sample(remainder, min(n - len(category_pool), len(remainder)))

    # Stufe 2 — Farb-Ranking innerhalb der Kategorie
    if color_hint:
        category_pool = sorted(category_pool, key=lambda e: _color_score(e, color_hint), reverse=True)

    # Stufe 3 — Top-n nehmen; bei Gleichstand etwas Varianz durch leichtes Shufflen der hinteren Ränge
    top = category_pool[:n]

    lines = []
    for s in top:
        origin = s.get("origin", "unknown")
        treatment = s.get("treatment", "unknown")
        colours = ", ".join(s.get("colours", [])) if s.get("colours") else ""
        colour_str = f" | colors: {colours}" if colours else ""
        lines.append(
            f'- "{s["name_raw"]}" | {s["carat"]}ct | {s["clarity"]} | '
            f'{origin} | {treatment}{colour_str} | ${s["price_usd"]:.0f}'
        )

    return "\n".join(lines)


LOOK_ALIKE_GUIDE = """
CRITICAL DISTINCTIONS — study these before identifying:

Cornflower Blue Sapphire vs Tanzanite:
- Cornflower Blue Sapphire: soft medium blue, color is STABLE from all angles, no violet-to-burgundy shift,
  Sri Lanka / Kashmir origin, hardness 9, higher price per carat than Tanzanite
- Tanzanite: violet-blue with STRONG trichroism (rotates through blue/violet/burgundy), Tanzania ONLY, hardness 6.5
  DECISION: if color is predominantly blue and STABLE across images → Cornflower Blue Sapphire, NOT Tanzanite

Blue Sapphire vs Aquamarine:
- Blue Sapphire: deeper blue, high brilliance, hardness 9
- Aquamarine: light pastel blue/greenish-blue, lower saturation, hardness 7.5-8

Ruby vs Red Spinel vs Red Garnet vs Rubellite:
- Ruby: pure red to slightly purplish-red, strong UV fluorescence, corundum
- Red Spinel: vivid neon red, no UV fluorescence, octahedral crystal
- Red Garnet (Pyrope/Almandine): brownish-dark red, no fluorescence
- Rubellite Tourmaline: pink to red, elongated crystal habit

Pink/Red Sapphire vs Ruby:
- Ruby: pure red to slightly purplish-red, Corundum, strong UV fluorescence
  Hardness 9, Burma/Mozambique/Thailand origin typical
- Pink Sapphire: pink to pinkish-red, same mineral (Corundum) as Ruby but lower chromium
  Kashmir Pink Sapphire: muted pinkish-violet, HEAVY inclusions (silk), velvety appearance
  DECISION: if stone shows heavy silk inclusions AND muted pinkish/violetish hue → Pink Sapphire,
  NOT Ruby. Pure vivid red without heavy inclusions → Ruby.

Emerald vs Tsavorite vs Chrome Tourmaline:
- Emerald: bluish-green, heavy inclusions (jardin), Colombia/Zambia/Brazil
- Tsavorite: vivid pure green, clean, Kenya/Tanzania
- Chrome Tourmaline: similar green, elongated prismatic crystals

Paraiba Tourmaline vs Blue/Green Tourmaline:
- Paraiba: NEON electric blue-green glow, copper-bearing, extremely rare
- Regular Tourmaline: lacks neon glow, muted colors

Alexandrite vs Color-Change Garnet:
- Alexandrite: green/teal in daylight, red/purple in incandescent light
- Color-Change Garnet: brownish-green to red/orange shift, more muted

Padparadscha Sapphire:
- Very specific pink-orange combination (salmon), Sri Lanka, extremely rare and valuable
"""


def build_vision_prompt(
    db: list,
    n_images: int = 1,
    gem_category: str | None = None,
    color_hint: str | None = None,
) -> str:
    examples = get_rag_examples(db, gem_category=gem_category, color_hint=color_hint, n=5)
    examples_block = f"Real market reference examples:\n{examples}\n" if examples else ""

    # Debug-Info für Logs (wird nicht an Modell geschickt)
    rag_info = f"[RAG] category={gem_category}, color={color_hint}, examples={len(examples.splitlines()) if examples else 0}"

    multi_note = ""
    if n_images > 1:
        multi_note = (
            f"You are analyzing {n_images} images of the SAME stone from different angles. "
            "Evaluate color stability across all images — stable color suggests Sapphire/Spinel/Garnet, "
            "strong color shift suggests Tanzanite/Alexandrite/Color-Change stone.\n"
        )

    print(f"[vision_prompt] {rag_info}")
    correction_hint = build_correction_hint()
    correction_block = f"{correction_hint}\n\n" if correction_hint else ""

    prompt = f"""You are an expert gemologist AI. Respond with ONLY a valid JSON object, nothing else.

{multi_note}
{LOOK_ALIKE_GUIDE}
{correction_block}
{examples_block}
Analyze the gemstone image carefully. Consider ALL visual evidence: color, hue, saturation, luster,
transparency, visible inclusions, and any color variation across images.

Return this exact JSON structure — fill in real values, do NOT describe the fields:
{{
  "candidates": [
    {{
      "stone_type": "exact stone name",
      "probability": 0.65,
      "color": "precise trade color name",
      "clarity_estimate": "VS",
      "carat_approx": null,
      "carat_estimated": false,
      "origin_probability": "country name",
      "reasoning": "specific visual evidence for this identification"
    }},
    {{
      "stone_type": "second most likely stone",
      "probability": 0.25,
      "color": "color description",
      "clarity_estimate": "VS",
      "carat_approx": null,
      "carat_estimated": false,
      "origin_probability": "country name",
      "reasoning": "why this could also be correct"
    }},
    {{
      "stone_type": "third possibility",
      "probability": 0.10,
      "color": "color description",
      "clarity_estimate": "VS",
      "carat_approx": null,
      "carat_estimated": false,
      "origin_probability": "country name",
      "reasoning": "brief reason"
    }}
  ],
  "overall_confidence": 0.70,
  "color_stability": "stable",
  "image_quality": "good",
  "notes": "any additional observation"
}}

Important: probabilities must sum to exactly 1.0. clarity_estimate must be one of: I1, SI2, SI1, VS, VVS.
color_stability must be one of: stable, slight_shift, strong_shift.
carat_approx is null unless a ruler, coin or finger provides a clear size reference."""

    return prompt
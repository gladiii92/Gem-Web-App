"""
enrich_clarity.py — Lädt Clarity von GemRock Detailseiten nach.
Besucht nur Einträge mit clarity=None. Schreibt direkt in crawl_db.json.
"""

import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

CRAWL_DB = Path(__file__).parent / "crawl_db.json"


def extract_clarity_from_detail_table(html: str) -> str | None:
    # Format A: <li>Clarity: VS but dark</li>
    match = re.search(r'Clarity:\s*([^<]{1,30})', html, re.IGNORECASE)
    if not match:
        # Format B: <dt class="...">Clarity</dt><dd>VS</dd>
        match = re.search(r'Clarity\s*</dt>\s*<dd[^>]*>\s*([^<]{1,20})', html, re.IGNORECASE)
    if not match:
        return None

    raw = match.group(1).strip().upper()

    # Explizit ungültige Werte rausfiltern
    if raw in ("N/A", "NA", "-", ""):
        return None

    grade_map = {
        "VVS": "VVS", "VS": "VS", "SI1": "SI1", "SI2": "SI2",
        "SI":  "SI1", "I1": "I1", "I2":  "I1",  "I":   "I1",
        "FL":  "VVS", "IF": "VVS",
    }

    if raw in grade_map:
        return grade_map[raw]

    for key in sorted(grade_map.keys(), key=len, reverse=True):
        if raw.startswith(key):
            return grade_map[key]

    return None


def run():
    with open(CRAWL_DB, "r", encoding="utf-8") as f:
        db = json.load(f)

    missing = [e for e in db if not e.get("clarity") and e.get("lot_url")]
    print(f"Einträge ohne Clarity: {len(missing)}/{len(db)}")
    print("Starte Enrichment...\n")

    enriched = 0
    failed   = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Session aufbauen
        page.goto("https://www.gemrockauctions.com", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        try:
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=5000)
            page.wait_for_timeout(1000)
            print("[setup] Cookie-Consent akzeptiert")
        except:
            print("[setup] Kein Cookie-Banner gefunden")

        for i, entry in enumerate(missing):
            url = entry["lot_url"]
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(500)
                html    = page.content()
                clarity = extract_clarity_from_detail_table(html)

                if clarity:
                    entry["clarity"] = clarity
                    enriched += 1
                else:
                    failed += 1

                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{len(missing)}] enriched={enriched} failed={failed}")

                time.sleep(0.3)

            except Exception as ex:
                failed += 1
                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}] Fehler: {ex}")

        browser.close()

    # Schreibe zurück
    with open(CRAWL_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Enrichment abgeschlossen")
    print(f"   Clarity nachgeladen : {enriched}")
    print(f"   Nicht gefunden      : {failed}")
    print(f"   Jetzt mit Clarity   : {len([e for e in db if e.get('clarity')])}/{len(db)}")


if __name__ == "__main__":
    run()
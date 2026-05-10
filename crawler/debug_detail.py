from playwright.sync_api import sync_playwright
import json
from pathlib import Path

CRAWL_DB = Path(__file__).parent / "crawl_db.json"
db = json.load(open(CRAWL_DB, encoding="utf-8"))
missing = [e for e in db if not e.get("clarity") and e.get("lot_url")]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # Session aufbauen — Hauptseite zuerst
    page.goto("https://www.gemrockauctions.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    try:
        page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=5000)
        page.wait_for_timeout(1000)
    except:
        pass

    # Jetzt Detailseiten aufrufen
    for entry in missing[:3]:
        url = entry["lot_url"]
        print(f"\nURL: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            html = page.content()
            idx = html.lower().find("clarity")
            print(f"  HTML-Länge: {len(html)} | clarity: {idx != -1}")
            if idx != -1:
                print(f"  → {html[idx:idx+60]}")
        except Exception as ex:
            print(f"  ❌ {ex}")

    browser.close()
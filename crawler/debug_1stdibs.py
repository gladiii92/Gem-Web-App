from playwright.sync_api import sync_playwright
import re

URL = "https://www.1stdibs.com/jewelry/loose-gemstones/natural-blue-sapphire-gemstone-156-carats-gia-report-jupitergem/id-j_23071262/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # sichtbar — damit du siehst was geladen wird
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="en-US",
    )
    page = context.new_page()
    page.goto("https://www.1stdibs.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    try:
        page.click("#onetrust-accept-btn-handler", timeout=3000)
        page.wait_for_timeout(1000)
    except:
        pass

    # domcontentloaded + extra wait statt networkidle
    page.goto(URL, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(5000)  # 5s warten bis JS fertig

    html = page.content()

    # Titel
    title = re.search(r'<title>(.*?)</title>', html)
    print(f"TITLE: {title.group(1) if title else 'fehlt'}")

    # Alle Preis-Pattern
    print("\n=== PREISE ===")
    prices = re.findall(r'[\$€]\s*[\d,]+(?:\.\d{2})?', html)
    print(f"Alle: {prices[:15]}")

    # OG price tag
    og_price = re.findall(r'content="([^"]*USD[^"]*|[\d,]+\.?\d*)"[^>]*property="[^"]*price[^"]*"', html, re.IGNORECASE)
    og_price2 = re.findall(r'property="[^"]*price[^"]*"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    print(f"OG price: {og_price[:5]}")
    print(f"OG price2: {og_price2[:5]}")

    # JSON mit price
    json_prices = re.findall(r'"price[^"]*":\s*"?([\d.,]+)"?', html, re.IGNORECASE)
    print(f"JSON price fields: {json_prices[:10]}")

    # innerText des Preis-Elements direkt auslesen
    try:
        price_text = page.locator('[data-tn*="price"], [class*="price"], [data-testid*="price"]').first.inner_text(timeout=3000)
        print(f"\nPreis-Element innerText: {price_text}")
    except:
        print("\nKein Preis-Element per Locator gefunden")

    input("Browser offen — schau dir die Seite an. Enter zum Beenden.")
    browser.close()
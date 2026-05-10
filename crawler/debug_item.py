# debug_item.py — einmalig ausführen, dann löschen
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ))
    page.goto("https://www.gemrockauctions.com/auctions/sapphire?type%5B0%5D=catalogue",
              wait_until="networkidle", timeout=30000)
    
    # Cookies akzeptieren
    try:
        btn = page.wait_for_selector("#CybotCookiebotDialogBodyButtonAccept", timeout=5000)
        btn.click()
        page.wait_for_timeout(1000)
    except:
        pass
    
    page.wait_for_selector(".ais-Hits-item", timeout=15000)
    
    soup  = BeautifulSoup(page.content(), "lxml")
    items = soup.select(".ais-Hits-item")
    
    # Erstes Item komplett ausgeben
    print("=== ERSTES .ais-Hits-item ===")
    print(items[0].prettify())
    
    browser.close()
# CRAWLER CONFIGURATION
# Passe EUR_TO_USD bei Bedarf manuell an
EUR_TO_USD = 1.08

# GemRock Zielkategorien — IDs 1-27 (bestehend) + 28-37 (neu)
GEMROCK_GEMS = [
    # Bestehende Kategorien
    "sapphire", "ruby", "emerald", "tourmaline", "spinel",
    "alexandrite", "garnet", "tanzanite", "topaz", "padparadscha",
    # Neue Kategorien 28-37
    "rubellite", "indicolite", "chrome-tourmaline", "watermelon-tourmaline",
    "rhodolite", "malaya-garnet", "color-change-garnet",
    "pyrope", "almandine", "morganite",
]

GEMROCK_BASE = "https://www.gemrockauctions.com"
GEMROCK_CATALOGUE  = GEMROCK_BASE + "/auctions/{gem}?type%5B0%5D=catalogue&page={page}"
GEMROCK_NORESERVE  = GEMROCK_BASE + "/auctions/no-reserve-gemstone-online-auctions?page={page}"

# Sekunden zwischen Requests — bitte nicht unter 2 setzen
REQUEST_DELAY        = 2.5   # Listing-Seiten
DETAIL_REQUEST_DELAY = 1.5   # Detailseiten (GemRock)

# Pfad zur Datenbank
DB_PATH = "crawl_db.json"
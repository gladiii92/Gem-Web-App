"""
MANUAL IMPORT — für Jason Brim Posts und andere manuelle Quellen.
Aufruf: python manual_import.py
"""
from datetime import datetime, timezone
from categorizer import categorize
from db import add_entries


def manual_entry(
    name: str,
    carat: float,
    price_usd: float,
    price_type: str = "retail",    # "retail" oder "wholesale"
    source: str = "manual_jason",
    clarity: str = None,
    treatment: str = "unknown",
    origin: str = None,
    image_url: str = None,
    notes: str = "",
) -> dict:
    entry = {
        "source_id":    f"{source}_{hash(name + str(carat) + str(price_usd))}",
        "source":       source,
        "price_type":   price_type,
        "name_raw":     name,
        "gem_category": name.lower().split()[0],
        "category":     None,
        "carat":        carat,
        "clarity":      clarity,
        "treatment":    treatment,
        "origin":       origin,
        "price_usd":    price_usd,
        "currency_raw": "USD",
        "image_url":    image_url,
        "lot_url":      None,
        "notes":        notes,
        "crawled_at":   datetime.now(timezone.utc).isoformat(),
    }
    return categorize(entry)


if __name__ == "__main__":
    print("=== Manueller Import ===")
    print("Beispiel: Jason Brim Post")
    print()

    # Beispiel-Eintrag — hier einfach weitere hinzufügen
    entries = [
        manual_entry(
            name="Afghanistan Tourmaline Cremesicle Orange",
            carat=3.30,
            price_usd=330,
            price_type="retail",
            clarity="SI1",      # eye clean
            treatment="unheated",
            origin="Afghanistan",
            notes="Jason Brim Facebook Post",
        ),
    ]

    added = add_entries(entries)
    print(f"✅ {added} neue Einträge gespeichert.")

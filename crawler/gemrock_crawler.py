"""
gemrock_crawler.py — GemRock Consolidated Crawler v5.3
"""

import re
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from config import (
    GEMROCK_GEMS,
    GEMROCK_CATALOGUE,
    GEMROCK_NORESERVE,
    REQUEST_DELAY,
    DETAIL_REQUEST_DELAY,
)
from parser import parse_gemrock_lot
from categorizer import categorize
from db import load_db, save_db

ALLOWED_CLARITIES = {"I1", "SI1", "SI2", "VS", "VVS"}

REMOVE_NAME_PATTERNS = [
    re.compile(r"\bHAND\s*CARVED\b", re.I),
    re.compile(r"\bSTAR\s*SAPPHIRE\b", re.I),
]

CABOCHON_PATTERNS = [
    re.compile(r"\bCABOCHON\b", re.I),
    re.compile(r"\bCAB\b", re.I),
    re.compile(r"\bSTAR\s*SAPPHIRE\b", re.I),
    re.compile(r"\bHAND\s*CARVED\b", re.I),
]

def accept_cookies(page):
    try:
        btn = page.wait_for_selector(
            "#CybotCookiebotDialogBodyButtonAccept, [id*='accept'], button:has-text('Accept')",
            timeout=5000,
        )
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
    except:
        pass

def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\[#.*?#\]", "", text)
    text = re.sub(
        r"(Consent Selection|Necessary Preferences|Captions|descriptions off|Picture-in-Picture|This is a modal window).*?Details",
        "",
        text,
        flags=re.I | re.DOTALL,
    )
    text = re.sub(
        r"Descriptions descriptions off.*?Fullscreen",
        "",
        text,
        flags=re.I | re.DOTALL,
    )
    return re.sub(r"\s+", " ", text).strip()

def should_remove_by_name(name: str | None) -> bool:
    if not name:
        return False
    return any(p.search(name) for p in REMOVE_NAME_PATTERNS)

def is_cabochon_text(text: str | None) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in CABOCHON_PATTERNS)

def _extract_after_label(text: str, label: str) -> str | None:
    if not text:
        return None
    m = re.search(
        rf"{re.escape(label)}\s*[:\-]?\s*([^\n\r|,;]+)",
        text,
        flags=re.I,
    )
    if not m:
        return None
    value = m.group(1).strip()
    if value.lower() in {"none", "null", "n/a", "na", ""}:
        return None
    return value

def _normalize_clarity_value(raw: str | None) -> str | None:
    if not raw:
        return None
    t = re.sub(r"\s+", " ", raw).strip().upper()

    if "FLAWLESS" in t:
        return "VVS"

    if re.search(r"\bVVS\b", t):
        return "VVS"
    if re.search(r"\bVS1\b", t) or re.search(r"\bVS2\b", t) or re.search(r"\bVS\b", t):
        return "VS"
    if re.search(r"\bSI2\b", t):
        return "SI2"
    if re.search(r"\bSI1\b", t):
        return "SI1"
    if re.search(r"\bSI\b", t):
        return "SI1"
    if re.search(r"\bI1\b", t):
        return "I1"
    if re.search(r"\bI\b", t):
        return "I1"
    return None

def _parse_treatment(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    if any(x in t for x in ["no treatment", "unheated", "untreated", "natural"]):
        return "unheated"
    if any(x in t for x in ["heated", "heat treatment", "beryllium", "glass"]):
        return "heated"
    return None

def _parse_origin(text: str) -> str | None:
    if not text:
        return None
    origins = [
        "sri lanka",
        "ceylon",
        "burma",
        "myanmar",
        "colombia",
        "brazil",
        "tanzania",
        "madagascar",
        "mozambique",
        "australia",
        "kenya",
        "afghanistan",
    ]
    t = text.lower()
    for o in origins:
        if o in t:
            return "Sri Lanka" if o == "ceylon" else o.title()
    return None

def _parse_certificate(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    if any(x in t for x in ["gia", "g.i.a", "gemological institute"]):
        return "GIA"
    if any(x in t for x in ["igi", "ssef", "hrd", "ags", "egl", "lab report", "certif"]):
        return "Certified"
    return None

def _parse_shape_from_text(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    shapes = ["oval", "round", "pear", "cushion", "emerald", "heart", "marquise", "fancy", "freeform", "square", "rectangle"]
    for s in shapes:
        if s in t:
            return s
    return None

def _extract_details_from_html(soup: BeautifulSoup) -> dict:
    details = {}
    candidates = soup.find_all(["dt", "th", "strong", "b", "label"])
    for elem in candidates:
        label_text = elem.get_text(strip=True)
        if not label_text or len(label_text) > 80:
            continue
        label_lower = label_text.lower()
        for sibling in elem.find_next_siblings(["dd", "td", "div", "span", "p"]):
            value = _clean_text(sibling.get_text(" ", strip=True))
            if value and len(value) < 200:
                details[label_lower] = value
                break
        if label_lower not in details:
            next_text = elem.next_sibling
            if next_text and isinstance(next_text, str):
                val = _clean_text(next_text)
                if val:
                    details[label_lower] = val
    return details

def fetch_detail_fields_gemrock(page, lot_url: str, lot_name: str | None = None) -> dict:
    if not lot_url:
        return {}

    full_url = lot_url if lot_url.startswith("http") else f"https://www.gemrockauctions.com{lot_url}"

    try:
        page.goto(full_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2200)

        try:
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=4000)
            page.wait_for_timeout(1000)
        except:
            pass

        soup = BeautifulSoup(page.content(), "lxml")
        full_text = soup.get_text(" ", strip=True)
        clean_full = _clean_text(full_text)

        details = _extract_details_from_html(soup)

        desc_match = re.search(
            r"(?:Description|Colours?\s+Description|Details).*?(?=Shipping Provider|You may also like|Similar Items|PAYMENT POLICY|COMBINE POLICY|REFUND|Thank You for choosing)",
            full_text,
            re.I | re.DOTALL,
        )
        description_raw = _clean_text(desc_match.group(0)) if desc_match else clean_full[:2500]

        if should_remove_by_name(lot_name):
            print(f" [SKIP] Name filter: {lot_name}")
            return {"skip": True, "reason": "name_filter", "description_raw": description_raw}

        if is_cabochon_text(description_raw) or is_cabochon_text(details.get("type", "")):
            print(f" [SKIP] Cabochon: {lot_url.split('/')[-1]}")
            return {"skip": True, "reason": "cabochon", "description_raw": "CABOCHON - SKIPPED"}

        clarity_raw = details.get("clarity")
        if clarity_raw is None or str(clarity_raw).strip().lower() in {"none", "null", "n/a", "na", ""}:
            clarity_raw = _extract_after_label(description_raw, "Clarity")
        clarity = _normalize_clarity_value(clarity_raw)

        if clarity is None and "FLAWLESS" in description_raw.upper():
            clarity = "VVS"

        result = {
            "clarity": clarity if clarity in ALLOWED_CLARITIES else None,
            "treatment": details.get("treatment") or _parse_treatment(description_raw),
            "origin": details.get("origin") or _parse_origin(description_raw),
            "shape": (details.get("shape") or _parse_shape_from_text(description_raw) or "").lower() or None,
            "cut": (details.get("type") or "").lower() or None,
            "dimensions_mm": details.get("dimensions (mm)") or details.get("dimensions"),
            "certificate": _parse_certificate(description_raw),
            "description_raw": description_raw if description_raw else None,
        }

        filled = [k for k, v in result.items() if v and k != "description_raw"]
        cert = f" | Cert: {result['certificate']}" if result.get("certificate") else ""
        print(f" → Gefüllt: {', '.join(filled) if filled else 'nichts'}{cert} | desc: {'✓' if result.get('description_raw') else '✗'}")

        return result

    except Exception as e:
        print(f" [ERROR] {lot_url}: {e}")
        return {}

def wait_for_items(page) -> bool:
    try:
        page.wait_for_selector(".ais-Hits-item", timeout=15000)
        return True
    except PlaywrightTimeout:
        return False

def scrape_listing_page(page, gem_category: str) -> list:
    soup = BeautifulSoup(page.content(), "lxml")
    items = soup.select(".ais-Hits-item")
    print(f" [listing] {len(items)} .ais-Hits-item gefunden")
    results = []
    for item in items:
        parsed = parse_gemrock_lot(item, gem_category)
        if parsed:
            parsed["crawled_at"] = datetime.now(timezone.utc).isoformat()
            results.append(categorize(parsed))
    return results

def go_to_next_page(page) -> bool:
    try:
        next_btn = page.query_selector(".ais-Pagination-item--nextPage:not(.ais-Pagination-item--disabled) a")
        if not next_btn:
            return False
        next_btn.click()
        page.wait_for_timeout(2000)
        wait_for_items(page)
        return True
    except:
        return False

def crawl_url(
    listing_page,
    detail_page,
    url: str,
    gem_category: str,
    existing_db: dict,
    mode: str = "update",
    max_pages: int = 10,
    price_type: str = "retail",
    batch_limit: int = 0,
    batch_counter: list = None,
) -> list:

    if batch_counter is None:
        batch_counter = [0]

    print(f" [crawler] -> {url}")
    try:
        listing_page.goto(url, wait_until="networkidle", timeout=30000)
    except PlaywrightTimeout:
        print(" [crawler] Timeout")
        return []

    accept_cookies(listing_page)
    if not wait_for_items(listing_page):
        return []

    all_results = []

    for page_num in range(1, max_pages + 1):
        if batch_limit > 0 and batch_counter[0] >= batch_limit:
            break

        lots = scrape_listing_page(listing_page, gem_category)
        print(f" [crawler] Seite {page_num}: {len(lots)} Lots geparst")

        for lot in lots:
            if batch_limit > 0 and batch_counter[0] >= batch_limit:
                break

            lot["price_type"] = price_type
            sid = lot.get("source_id")
            lot_name = lot.get("name_raw")

            if should_remove_by_name(lot_name):
                print(f" [SKIP] Name filter: {sid}")
                continue

            if mode == "incremental" and sid in existing_db:
                continue

            if mode == "update" and sid in existing_db:
                existing = existing_db[sid]
                if existing.get("description_raw"):
                    continue
                print(f" [detail] Update für {sid}")
                extra = fetch_detail_fields_gemrock(detail_page, lot.get("lot_url"), lot_name=lot_name)
                if extra.get("skip"):
                    continue
                for field in ["clarity", "treatment", "origin", "shape", "cut", "dimensions_mm", "certificate", "description_raw"]:
                    if field in extra and extra[field]:
                        existing[field] = extra[field]
                existing_db[sid] = existing
                time.sleep(DETAIL_REQUEST_DELAY)
                continue

            if lot.get("lot_url"):
                print(f" [detail] Voll-Extraktion für {sid}")
                extra = fetch_detail_fields_gemrock(detail_page, lot.get("lot_url"), lot_name=lot_name)
                if extra.get("skip"):
                    continue
                if extra:
                    for field in ["clarity", "treatment", "origin", "shape", "cut", "dimensions_mm", "certificate", "description_raw"]:
                        if field in extra and extra[field]:
                            lot[field] = extra[field]

            all_results.append(lot)
            batch_counter[0] += 1

        if not go_to_next_page(listing_page):
            break

        time.sleep(REQUEST_DELAY)

    return all_results

def run(mode: str = "update", max_pages: int = 10, batch_limit: int = 0, catalogue: bool = True, no_reserve: bool = True):
    db = load_db()
    existing_db = {e["source_id"]: e for e in db if "source_id" in e}
    print(f"[db] {len(db)} Einträge geladen")

    total_new = 0
    batch_counter = [0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        listing_page = context.new_page()
        detail_page = context.new_page()

        listing_page.goto("https://www.gemrockauctions.com", wait_until="networkidle", timeout=20000)
        accept_cookies(listing_page)

        if catalogue:
            for gem in GEMROCK_GEMS:
                if batch_limit > 0 and batch_counter[0] >= batch_limit:
                    break
                print(f"\n=== Katalog: {gem.upper()} ===")
                url = GEMROCK_CATALOGUE.format(gem=gem, page=1)
                new_lots = crawl_url(
                    listing_page,
                    detail_page,
                    url,
                    gem,
                    existing_db,
                    mode,
                    max_pages,
                    "retail",
                    batch_limit,
                    batch_counter,
                )
                for lot in new_lots:
                    existing_db[lot["source_id"]] = lot
                    total_new += 1
                print(f" [db] {len(new_lots)} neue Einträge für {gem}")
                time.sleep(REQUEST_DELAY * 2)

        browser.close()

    final_db = list(existing_db.values())
    save_db(final_db)
    print(f"\n✅ GemRock fertig. Neu: {total_new} | DB gesamt: {len(final_db)}")

    script_dir = Path(__file__).parent
    for script in ["recategorize.py", "aggregator.py"]:
        print(f"[pipeline] Starte {script} ...")
        try:
            subprocess.run(["python", script], check=True, cwd=script_dir)
            print(f" {script} → OK")
        except Exception as e:
            print(f" ⚠️ {script}: {e}")

    print("\n✅ Pipeline abgeschlossen.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["update", "incremental"], default="update")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--batch", type=int, default=0)
    args = parser.parse_args()

    run(mode=args.mode, max_pages=args.max_pages, batch_limit=args.batch)
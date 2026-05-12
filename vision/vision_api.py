"""
vision_api.py v4.0 — RAG-Integration + Feedback-Endpoint
"""

import base64
import hashlib
import io
import json
import re
import requests
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from vision_prompt import load_db, build_vision_prompt, build_pass1_prompt, STONE_TO_CATEGORY

app = Flask(__name__)
CORS(app)

OLLAMA_URL      = "http://localhost:11434/api/generate"
VISION_MODEL    = "qwen2.5vl:7b"
TIMEOUT_SEC     = 600
MAX_IMG_SIZE    = (1024, 1024)
CORRECTIONS_DB = Path(__file__).parent.parent / "crawler" / "gems.db"

_db = load_db()
print(f"[vision_api] DB geladen: {len(_db)} Einträge")


# ── Bild-Utilities ───────────────────────────────────────────────────────────

def image_to_base64(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


def resize_image(file_bytes: bytes, max_size: tuple = MAX_IMG_SIZE) -> bytes:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        resized = out.getvalue()
        print(f"[vision_api] Bild: {len(file_bytes)//1024}KB → {len(resized)//1024}KB")
        return resized
    except Exception as e:
        print(f"[vision_api] Resize-Fehler: {e}")
        return file_bytes


def extract_color_hint(image_bytes: bytes) -> str | None:
    """
    Extrahiert dominanten Farbton via gesättigteste Pixel (Top-20%).
    Ignoriert Hintergrund und dunkle/helle Extremwerte.
    """
    try:
        from PIL import Image
        import colorsys

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((64, 64), Image.LANCZOS)
        pixels = list(img.getdata())

        # Nur gesättigte Pixel verwenden (S > 0.2, V > 0.15 und < 0.95)
        saturated = []
        for r, g, b in pixels:
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            if s > 0.2 and 0.15 < v < 0.95:
                saturated.append((h, s, v))

        # Fallback: wenn zu wenig gesättigte Pixel → Stein ist weiß/schwarz/grau
        if len(saturated) < len(pixels) * 0.05:
            avg_v = sum(p[2] for p in [colorsys.rgb_to_hsv(r/255,g/255,b/255) for r,g,b in pixels]) / len(pixels)
            return "white" if avg_v > 0.6 else "black"

        # Durchschnittlicher Hue der gesättigtesten Pixel
        avg_h = sum(p[0] for p in saturated) / len(saturated)

        # Hue (0–1 in Pillow/colorsys) → Farb-Kategorie
        h360 = avg_h * 360
        if h360 < 20 or h360 >= 340:
            return "red"
        if h360 < 45:
            return "orange"
        if h360 < 75:
            return "yellow"
        if h360 < 165:
            return "green"
        if h360 < 255:
            return "blue"
        if h360 < 290:
            return "purple"
        if h360 < 340:
            return "pink"
        return None

    except Exception as e:
        print(f"[vision_api] color_hint Fehler: {e}")
        return None


def image_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()[:12]


# ── Ollama ───────────────────────────────────────────────────────────────────

def warmup_model():
    try:
        print(f"[vision_api] Lade {VISION_MODEL} in VRAM...")
        requests.post(OLLAMA_URL, json={
            "model": VISION_MODEL,
            "prompt": "hello",
            "stream": False,
            "keep_alive": "30m",
        }, timeout=120)
        print(f"[vision_api] Modell bereit.")
    except Exception as e:
        print(f"[vision_api] Warmup fehlgeschlagen: {e}")


def extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    for m in re.finditer(r"\{", text):
        for end in range(len(text), m.start(), -1):
            try:
                result = json.loads(text[m.start():end])
                if "candidates" in result:
                    return result
            except Exception:
                continue
    raise ValueError(f"Kein gültiges JSON gefunden. Output-Anfang: {text[:400]}")


def call_ollama_vision(images_b64: list, prompt: str) -> dict:
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": images_b64,
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 800,
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SEC)

    if resp.status_code != 200:
        raw = resp.text[:500]
        print(f"[vision_api] Ollama HTTP {resp.status_code}: {raw}")
        try:
            err_msg = resp.json().get("error", raw)
        except Exception:
            err_msg = raw
        if "out of memory" in err_msg.lower():
            raise ValueError("VRAM voll — weniger Bilder oder Ollama neu starten")
        raise ValueError(f"Ollama Fehler: {err_msg}")

    raw_text = resp.json().get("response", "")
    print(f"[vision_api] Output ({len(raw_text)} Zeichen): {raw_text[:300]}")
    return extract_json(raw_text)

def call_ollama_pass1(images_b64: list) -> str | None:
    """
    Pass 1 — schneller Call, gibt nur gem_category zurück.
    num_predict: 40, kein volles JSON nötig.
    """
    payload = {
        "model": VISION_MODEL,
        "prompt": build_pass1_prompt(),
        "images": images_b64,
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {
            "temperature": 0.1,
            "num_predict": 40,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        raw = resp.json().get("response", "")
        print(f"[vision_api] Pass 1 raw: {raw[:100]}")
        data = json.loads(raw.strip())
        category = data.get("gem_category", "").lower().strip()
        valid = {
            "sapphire","ruby","emerald","tourmaline","spinel",
            "tanzanite","garnet","topaz","alexandrite","morganite"
        }
        return category if category in valid else None
    except Exception as e:
        print(f"[vision_api] Pass 1 fehlgeschlagen: {e}")
        return None


# ── Corrections-Helper ───────────────────────────────────────────────────────

def load_corrections() -> list:
    if not CORRECTIONS_DB.exists():
        return []
    conn = sqlite3.connect(CORRECTIONS_DB)
    rows = conn.execute(
        "SELECT predicted, correct, image_hash, timestamp FROM corrections ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"predicted": r[0], "correct": r[1],
             "image_hash": r[2], "timestamp": r[3]} for r in rows]


def save_correction(entry: dict):
    conn = sqlite3.connect(CORRECTIONS_DB)
    conn.execute(
        "INSERT INTO corrections (predicted, correct, image_hash, timestamp) VALUES (?,?,?,?)",
        (entry.get("predicted"), entry.get("correct"),
         entry.get("image_hash"), entry.get("timestamp"))
    )
    conn.commit()
    conn.close()
    print(f"[vision_api] Correction gespeichert: {entry}")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        model_available = any(VISION_MODEL in m for m in models)
        return jsonify({
            "status": "ok",
            "model": VISION_MODEL,
            "model_available": model_available,
            "db_entries": len(_db),
            "corrections_count": len(load_corrections()),
            "timeout_sec": TIMEOUT_SEC,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/analyze", methods=["POST"])
def analyze():
    images_b64 = []
    first_image_bytes = None
    allowed = {"jpg", "jpeg", "png", "webp"}

    for field in ["image", "image2", "image3"]:
        if field not in request.files:
            continue
        file = request.files[field]
        if not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in allowed:
            return jsonify({"error": f"Format nicht unterstützt: {ext}"}), 400
        image_bytes = file.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            return jsonify({"error": f"{field} zu groß (max. 10MB)"}), 400
        resized = resize_image(image_bytes)
        if first_image_bytes is None:
            first_image_bytes = image_bytes  # Original für color_hint (vor JPEG-Kompression)
        images_b64.append(image_to_base64(resized))

    if not images_b64:
        return jsonify({"error": "Mindestens ein Bild erforderlich"}), 400

    # RAG-Parameter aus Bild extrahieren
    color_hint = extract_color_hint(first_image_bytes) if first_image_bytes else None
    print(f"[vision_api] Analysiere {len(images_b64)} Bild(er) | color_hint={color_hint}")

    # gem_category: noch nicht bekannt vor Ollama-Call → None (Stufe 1 entfällt beim ersten Call)
    # Nach dem Call könnte man einen zweiten gezielteren Call machen — das ist Schritt 7B-Advanced
    # Pass 1 — gem_category schnell ermitteln (~15-25s)
    gem_category = call_ollama_pass1(images_b64)
    print(f"[vision_api] Pass 1 → gem_category={gem_category}")

    # Pass 2 — voller Call mit kategorie-gefiltertem RAG
    prompt = build_vision_prompt(_db, n_images=len(images_b64), gem_category=gem_category, color_hint=color_hint)

    try:
        result = call_ollama_vision(images_b64, prompt)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Ollama nicht erreichbar"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": f"Timeout nach {TIMEOUT_SEC}s — Ollama hängt, bitte neu starten"}), 504
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        print(f"[vision_api] Fehler: {type(e).__name__}: {e}")
        return jsonify({"error": str(e)}), 500

    # Karat aus Formular übernehmen
    user_carat = request.form.get("carat")
    if user_carat:
        try:
            cv = float(user_carat)
            for c in result.get("candidates", []):
                c["carat_approx"] = cv
                c["carat_estimated"] = False
        except ValueError:
            pass

    # image_hash für Feedback-Loop mitschicken
    img_hash = image_hash(first_image_bytes) if first_image_bytes else None
    result["images_analyzed"] = len(images_b64)
    result["image_hash"] = img_hash
    result["rag_color_hint"] = color_hint  # Debug-Info im Response
    result["rag_gem_category"] = gem_category  # Debug-Info

    return jsonify(result)


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Erwartet JSON: { "predicted": "Tanzanit", "correct": "Spinell", "image_hash": "abc123" }
    Speichert in corrections.json für späteren Feedback-Loop.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body erforderlich"}), 400

    predicted = data.get("predicted", "").strip()
    correct   = data.get("correct", "").strip()
    img_hash  = data.get("image_hash", "")

    if not predicted or not correct:
        return jsonify({"error": "predicted und correct sind Pflichtfelder"}), 400

    entry = {
        "predicted":  predicted,
        "correct":    correct,
        "image_hash": img_hash,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
    save_correction(entry)
    return jsonify({"status": "saved", "total_corrections": len(load_corrections())})


if __name__ == "__main__":
    warmup_model()
    print(f"[vision_api] http://localhost:5000 | Timeout: {TIMEOUT_SEC}s | keep_alive: 30m")
    app.run(host="0.0.0.0", port=5000, debug=False)
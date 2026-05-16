"""
generate_worker.py — schreibt data.json direkt in Cloudflare KV
Kein Dashboard-Klick mehr nötig.

Workflow:
  python crawler/aggregator.py   → data.json aktualisieren
  python generate_worker.py      → data.json → Cloudflare KV
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ── Credentials aus .env laden ──────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("[ERROR] .env nicht gefunden")
        sys.exit(1)
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env

env            = load_env()
ACCOUNT_ID     = env.get("CLOUDFLARE_ACCOUNT_ID", "")
NAMESPACE_ID   = env.get("CF_NAMESPACE_ID", "")
API_TOKEN      = env.get("CLOUDFLARE_API_TOKEN", "")
DATA_JSON      = Path(__file__).parent / "data.json"

if not all([ACCOUNT_ID, NAMESPACE_ID, API_TOKEN]):
    print("[ERROR] CLOUDFLARE_ACCOUNT_ID, CF_NAMESPACE_ID oder CF_API_TOKEN fehlen in .env")
    sys.exit(1)

# ── data.json laden ──────────────────────────────────────────────────────────
if not DATA_JSON.exists():
    print(f"[ERROR] data.json nicht gefunden: {DATA_JSON}")
    sys.exit(1)

with open(DATA_JSON, encoding="utf-8") as f:
    data = json.load(f)

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
size_kb = len(payload.encode("utf-8")) / 1024
print(f"[generate_worker] data.json geladen: {len(data)} Einträge, {size_kb:.1f} KB")

# ── In Cloudflare KV schreiben ───────────────────────────────────────────────
url = (
    f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}"
    f"/storage/kv/namespaces/{NAMESPACE_ID}/values/gems"
)

req = urllib.request.Request(
    url,
    data=payload.encode("utf-8"),
    method="PUT",
    headers={
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type":  "application/json",
    },
)

print(f"[generate_worker] Schreibe nach KV → key: gems ...")

try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
        if body.get("success"):
            print(f"[generate_worker] ✅ KV aktualisiert — {len(data)} Einträge live")
        else:
            print(f"[generate_worker] ❌ Fehler: {body.get('errors')}")
            sys.exit(1)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"[generate_worker] ❌ HTTP {e.code}: {body}")
    sys.exit(1)
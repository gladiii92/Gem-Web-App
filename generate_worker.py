# generate_worker.py — einmalig ausführen nach jedem aggregator.py Run
import json
from pathlib import Path

data = json.loads(Path("data.json").read_text(encoding="utf-8"))
worker_template = Path("workers/worker_template.js").read_text(encoding="utf-8")
output = worker_template.replace("__GEM_DATA_PLACEHOLDER__", json.dumps(data, ensure_ascii=False))
Path("workers/index.js").write_text(output, encoding="utf-8")
print(f"✅ workers/index.js generiert — {len(data)} Steine")
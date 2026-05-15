import json
from pathlib import Path

data = json.loads(Path("data.json").read_text(encoding="utf-8"))
print(len(data))
print(data[0]["id"], data[0]["name"])
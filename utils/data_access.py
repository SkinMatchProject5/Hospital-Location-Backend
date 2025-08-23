from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional


def load_jsonl(path: str) -> List[Dict]:
    records: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def index_parents(parents_path: str) -> Dict[str, Dict]:
    parents = load_jsonl(parents_path)
    by_id: Dict[str, Dict] = {}
    for p in parents:
        pid = p.get("id") or p.get("parent_id")
        if pid:
            by_id[pid] = p
    return by_id


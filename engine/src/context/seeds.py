"""
Deep Memory — seed compression for resolved content.

When content in Tier 2 is resolved (errors fixed, decisions made, tasks done),
compress it into seeds with ~60% compression and 100% fidelity. Seeds are
short pointers that preserve all names, amounts, deadlines, and links.
Full detail moves to cold storage.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


class SeedStore:

    def __init__(self, data_dir: str = "memra_data/seeds"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return os.path.join(self.data_dir, f"{safe}.jsonl")

    def _cold_path(self, session_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return os.path.join(self.data_dir, f"{safe}_cold.jsonl")

    def create_seed(self, session_id: str, summary: str, full_content: str, *,
                    category: str = "general", metadata: Optional[Dict] = None) -> Dict:
        seed = {
            "id": f"seed-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "category": category,
            "metadata": metadata or {},
        }

        with open(self._path(session_id), "a") as f:
            f.write(json.dumps(seed) + "\n")

        cold_entry = {**seed, "full_content": full_content}
        with open(self._cold_path(session_id), "a") as f:
            f.write(json.dumps(cold_entry) + "\n")

        return seed

    def get_seeds(self, session_id: str) -> List[Dict]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return []
        seeds = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    seeds.append(json.loads(line))
        return seeds

    def get_cold_detail(self, session_id: str, seed_id: str) -> Optional[Dict]:
        path = self._cold_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get("id") == seed_id:
                        return entry
        return None

    def render_seeds_context(self, session_id: str) -> str:
        seeds = self.get_seeds(session_id)
        if not seeds:
            return ""
        lines = ["## Deep Memory (Seeds)"]
        for s in seeds[-10:]:
            lines.append(f"- [{s['category']}] {s['summary']}")
        return "\n".join(lines)

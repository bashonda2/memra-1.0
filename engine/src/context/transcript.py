"""
Tier 1 — Immutable transcript store.

Ground truth. Every exchange is appended verbatim as JSONL.
Never modified, never deleted. The auditor compares Tier 2 against this.
"""
import json
import os
from datetime import datetime, timezone
from typing import List, Optional


class TranscriptWriter:

    def __init__(self, data_dir: str = "memra_data/transcripts"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return os.path.join(self.data_dir, f"{safe}.jsonl")

    def append(self, session_id: str, role: str, content: str, *,
               turn: int = 0, domain: str = "unknown") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": turn,
            "role": role,
            "content": content,
            "domain": domain,
        }
        with open(self._path(session_id), "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self, session_id: str) -> List[dict]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return []
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def read_last_n_turns(self, session_id: str, n: int) -> List[dict]:
        entries = self.read_all(session_id)
        if not entries:
            return []
        max_turn = max(e.get("turn", 0) for e in entries)
        cutoff = max(0, max_turn - n + 1)
        return [e for e in entries if e.get("turn", 0) >= cutoff]

    def turn_count(self, session_id: str) -> int:
        entries = self.read_all(session_id)
        if not entries:
            return 0
        turns = set(e.get("turn", 0) for e in entries)
        return len(turns)

    def list_sessions(self) -> List[str]:
        sessions = []
        for f in os.listdir(self.data_dir):
            if f.endswith(".jsonl"):
                sessions.append(f[:-6])
        return sorted(sessions)

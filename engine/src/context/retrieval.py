"""
Tier 3 — Vector retrieval (stub for v1.0).

When Tier 2 compresses away a detail, Tier 3 retrieves it via
semantic search. Requires ChromaDB or similar in v1.1+.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RetrievalResult:
    session_id: str
    turn: int
    role: str
    content: str
    score: float

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "turn": self.turn,
            "role": self.role,
            "content": self.content[:200],
            "score": self.score,
        }


class RetrievalLayer:
    """Stub — returns empty results until ChromaDB is wired in v1.1."""

    def __init__(self, data_dir: str = "memra_data/vectors"):
        self.data_dir = data_dir
        self.is_ready = False

    async def index_turn(self, session_id: str, turn: int, role: str, content: str) -> None:
        pass

    async def search(self, query: str, *, session_id: Optional[str] = None,
                     top_k: int = 5) -> List[RetrievalResult]:
        return []

"""Vector store substrate for semantic retrieval (EIAS sec.8 "Vector Memory Store").

Dev/test implementation: pure-Python, in-process, brute-force cosine similarity. This is a
storage-and-retrieval substrate only - it does not compute embeddings (no model is called
here). Production deployment swaps this for a real vector database (pgvector, etc.); the
interface (`add`, `search`) is deliberately small so that swap doesn't touch callers.
Same test-only-substitution pattern as shared/db.py's SQLite-for-Postgres swap - see
Documentation/operations/technology_decisions.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)


class InMemoryVectorStore:
    """A single in-process vector index. One instance per logical collection
    (e.g. one per memory tier, or one shared index filtered by metadata)."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    def add(self, id: str, vector: list[float], metadata: dict | None = None) -> None:
        self._records[id] = VectorRecord(id=id, vector=vector, metadata=metadata or {})

    def get(self, id: str) -> VectorRecord | None:
        return self._records.get(id)

    def delete(self, id: str) -> None:
        self._records.pop(id, None)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """Return up to `top_k` (id, similarity) pairs, highest similarity first."""

        scored = [
            (record.id, _cosine_similarity(query_vector, record.vector))
            for record in self._records.values()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def __len__(self) -> int:
        return len(self._records)

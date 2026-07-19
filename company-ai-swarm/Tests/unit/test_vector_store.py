"""Phase 2: vector store substrate. Synthetic vectors only - no embedding model is exercised
here, this proves storage + similarity search, not semantic quality."""

from __future__ import annotations

import pytest

from shared.vector_store import InMemoryVectorStore


@pytest.fixture()
def store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


def test_add_and_get(store: InMemoryVectorStore) -> None:
    store.add("MEM-001", [1.0, 0.0, 0.0], metadata={"tier": "working"})

    record = store.get("MEM-001")

    assert record is not None
    assert record.vector == [1.0, 0.0, 0.0]
    assert record.metadata == {"tier": "working"}


def test_search_ranks_by_similarity(store: InMemoryVectorStore) -> None:
    store.add("identical", [1.0, 0.0, 0.0])
    store.add("orthogonal", [0.0, 1.0, 0.0])
    store.add("opposite", [-1.0, 0.0, 0.0])

    results = store.search([1.0, 0.0, 0.0], top_k=3)

    ids_in_order = [r[0] for r in results]
    assert ids_in_order == ["identical", "orthogonal", "opposite"]
    assert results[0][1] == pytest.approx(1.0)
    assert results[1][1] == pytest.approx(0.0)
    assert results[2][1] == pytest.approx(-1.0)


def test_search_respects_top_k(store: InMemoryVectorStore) -> None:
    for i in range(10):
        store.add(f"MEM-{i}", [float(i), 0.0, 0.0])

    results = store.search([5.0, 0.0, 0.0], top_k=3)

    assert len(results) == 3


def test_dimension_mismatch_raises(store: InMemoryVectorStore) -> None:
    store.add("MEM-001", [1.0, 0.0, 0.0])

    with pytest.raises(ValueError, match="dimension mismatch"):
        store.search([1.0, 0.0])


def test_delete_removes_record(store: InMemoryVectorStore) -> None:
    store.add("MEM-001", [1.0, 0.0, 0.0])
    store.delete("MEM-001")

    assert store.get("MEM-001") is None
    assert len(store) == 0

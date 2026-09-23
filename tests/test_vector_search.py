import random

import pytest

from contextflow.storage.local import InMemoryVectorStore, cosine_similarity
from contextflow.storage.local_persistent import FileVectorStore


def _brute_force(vectors, query, limit):
    scored = [(i, cosine_similarity(query, v)) for i, v in vectors.items()]
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored[:limit]


@pytest.mark.parametrize("make_store", [InMemoryVectorStore, "file"])
def test_vectorized_search_matches_pure_python_cosine(make_store, tmp_path):
    store = FileVectorStore(str(tmp_path / "v.json")) if make_store == "file" else make_store()
    rng = random.Random(0)
    vectors = {f"d{i}": [rng.uniform(-1, 1) for _ in range(16)] for i in range(200)}
    vectors["zero"] = [0.0] * 16
    store.upsert_batch([(k, v, {}) for k, v in vectors.items()])
    query = [rng.uniform(-1, 1) for _ in range(16)]

    got = store.search(query, limit=10)
    want = _brute_force(vectors, query, 10)
    assert [i for i, _ in got] == [i for i, _ in want]
    assert all(abs(g - w) < 1e-5 for (_, g), (_, w) in zip(got, want, strict=True))

    # An upsert after a search must be visible to the next search.
    store.upsert("best", query, {})
    assert store.search(query, limit=1)[0][0] == "best"


def test_search_falls_back_for_mixed_dimensions():
    store = InMemoryVectorStore()
    store.upsert("a", [1.0, 0.0], {})
    store.upsert("b", [1.0, 0.0, 0.0], {})
    assert [i for i, _ in store.search([1.0, 0.0], limit=2)] == ["a", "b"]
    assert store.search([1.0, 0.0], limit=0) == []

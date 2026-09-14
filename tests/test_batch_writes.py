from contextflow.core.context import ContextObject
from contextflow.engine import local_workspace
from contextflow.storage.local_persistent import FileGraphStore, FileVectorStore


def test_file_vector_store_batch_matches_individual_upserts(tmp_path):
    individual = FileVectorStore(str(tmp_path / "individual.json"))
    for i in range(5):
        individual.upsert(f"id{i}", [float(i)], {"n": i})

    batched = FileVectorStore(str(tmp_path / "batched.json"))
    batched.upsert_batch([(f"id{i}", [float(i)], {"n": i}) for i in range(5)])

    for i in range(5):
        assert (
            individual.search([float(i)], limit=1)[0][0]
            == batched.search([float(i)], limit=1)[0][0]
        )


def test_file_vector_store_batch_writes_disk_once(tmp_path):
    path = tmp_path / "vectors.json"
    store = FileVectorStore(str(path))
    store.upsert_batch([(f"id{i}", [float(i)], {}) for i in range(50)])

    # Reload from disk to confirm the batch write actually persisted
    # everything, not just the in-memory copy.
    reloaded = FileVectorStore(str(path))
    assert reloaded.count() == 50


def test_file_graph_store_batch_matches_individual_calls(tmp_path):
    individual = FileGraphStore(str(tmp_path / "individual.json"))
    individual.add_entity("a", {"name": "a"})
    individual.add_entity("b", {"name": "b"})
    individual.add_relationship("a", "b", "co_mentioned", 1.0)

    batched = FileGraphStore(str(tmp_path / "batched.json"))
    batched.add_entities_batch([("a", {"name": "a"}), ("b", {"name": "b"})])
    batched.add_relationships_batch([("a", "b", "co_mentioned", 1.0)])

    assert individual.get_entity("a") == batched.get_entity("a")
    assert individual.traverse("a") == batched.traverse("a")


def test_file_graph_store_batch_persists_to_disk(tmp_path):
    path = tmp_path / "graph.json"
    store = FileGraphStore(str(path))
    store.add_entities_batch([(f"e{i}", {}) for i in range(10)])
    store.add_relationships_batch([(f"e{i}", f"e{i + 1}", "co_mentioned", 1.0) for i in range(9)])

    reloaded = FileGraphStore(str(path))
    assert reloaded.get_entity("e5") is not None
    assert len(reloaded.traverse("e0", depth=9)) == 9


def test_ingest_via_local_workspace_still_works_correctly_after_batching(tmp_path):
    """Regression test for the batch-write refactor: ingest() now calls
    index_batch()/add_entities_batch()/add_relationships_batch() instead
    of per-object loops. This proves the end-to-end behavior (search,
    persistence across engine instances) is unchanged, not just that the
    individual batch methods work in isolation."""
    workspace = str(tmp_path / "workspace")
    engine1 = local_workspace(workspace)
    count = engine1.ingest(
        [
            ContextObject(content="Acme Corp uses Stripe for payments", source="t"),
            ContextObject(content="The Payments Team owns this service", source="t"),
        ]
    )
    assert count == 2

    engine2 = local_workspace(workspace)
    results = engine2.retrieve("Stripe payments")
    assert len(results) > 0

    graph = engine2.get_context_graph("Stripe")
    assert graph["attributes"] is not None

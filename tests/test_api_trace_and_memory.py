from fastapi.testclient import TestClient

from contextflow.api.app import create_app
from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine
from contextflow.memory.store import MemoryStore


def _client(tmp_path=None) -> TestClient:
    engine = ContextEngine()
    engine.ingest([ContextObject(content="Stripe was selected for payments", source="t")])
    memory_store = MemoryStore(path=str(tmp_path / "memory.db")) if tmp_path else None
    app = create_app(engine=engine, memory_store=memory_store)
    return TestClient(app)


def test_trace_endpoint_returns_pipeline_stages():
    client = _client()
    resp = client.post("/v1/trace", json={"query": "payments", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "stages" in data
    names = [s["name"] for s in data["stages"]]
    assert "route" in names
    assert "rerank" in names


def test_memory_remember_and_recall_roundtrip(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/v1/memory/remember",
        json={"scope": "user", "scope_id": "alice", "fact": "Prefers annual contracts"},
    )
    assert resp.status_code == 200
    assert "id" in resp.json()

    resp2 = client.post(
        "/v1/memory/recall", json={"scope": "user", "scope_id": "alice", "query": "contracts"}
    )
    assert resp2.status_code == 200
    entries = resp2.json()
    assert len(entries) == 1
    assert "annual contracts" in entries[0]["content"]


def test_memory_scoped_by_scope_id(tmp_path):
    client = _client(tmp_path)
    client.post(
        "/v1/memory/remember", json={"scope": "user", "scope_id": "alice", "fact": "alice fact"}
    )
    client.post(
        "/v1/memory/remember", json={"scope": "user", "scope_id": "bob", "fact": "bob fact"}
    )
    resp = client.post("/v1/memory/recall", json={"scope": "user", "scope_id": "alice"})
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["content"] == "alice fact"

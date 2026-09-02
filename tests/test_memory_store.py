from contextflow.memory.store import MemoryStore


def test_remember_and_recall_roundtrip(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    store.remember("user", "alice", "Prefers annual contracts")
    store.remember("user", "alice", "Based in the EU, needs GDPR compliance")
    store.remember("user", "bob", "Prefers monthly billing")

    alice_facts = store.recall("user", "alice")
    assert len(alice_facts) == 2
    assert all(e.scope_id == "alice" for e in alice_facts)


def test_recall_ranks_by_keyword_relevance(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    store.remember("user", "alice", "Prefers annual contracts over monthly")
    store.remember("user", "alice", "Timezone is US Eastern")
    store.remember("user", "alice", "Contract renewal is due in December")

    results = store.recall("user", "alice", query="contract renewal")
    assert results
    assert "renewal" in results[0].content.lower() or "contract" in results[0].content.lower()


def test_forget_removes_entry(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    entry_id = store.remember("session", "sess1", "Ephemeral note")
    assert len(store.all("session", "sess1")) == 1

    assert store.forget(entry_id) is True
    assert len(store.all("session", "sess1")) == 0
    assert store.forget(entry_id) is False  # already gone


def test_persists_across_store_instances(tmp_path):
    path = str(tmp_path / "memory.db")
    store1 = MemoryStore(path=path)
    store1.remember("org", "acme", "Standard payment terms: net 30")

    store2 = MemoryStore(path=path)
    facts = store2.recall("org", "acme")
    assert len(facts) == 1
    assert "net 30" in facts[0].content


def test_metadata_is_persisted(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    store.remember("agent", "research-bot", "Found relevant paper", metadata={"source": "arxiv"})
    facts = store.recall("agent", "research-bot")
    assert facts[0].metadata == {"source": "arxiv"}


def test_scopes_are_isolated_from_each_other(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    store.remember("user", "shared-id", "user fact")
    store.remember("agent", "shared-id", "agent fact")

    user_facts = store.recall("user", "shared-id")
    agent_facts = store.recall("agent", "shared-id")
    assert len(user_facts) == 1
    assert len(agent_facts) == 1
    assert user_facts[0].content != agent_facts[0].content

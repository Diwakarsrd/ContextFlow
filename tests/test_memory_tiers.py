from contextflow.memory.agent import AgentMemory
from contextflow.memory.organization import OrganizationMemory
from contextflow.memory.session import SessionMemory
from contextflow.memory.store import MemoryStore
from contextflow.memory.user import UserMemory


def test_session_memory_remember_and_recall(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    mem = SessionMemory("sess-abc", store=store)
    mem.remember("User asked about refund policy")
    results = mem.recall()
    assert len(results) == 1
    assert "refund" in results[0].content


def test_user_memory_persists_across_sessions(tmp_path):
    path = str(tmp_path / "memory.db")
    mem1 = UserMemory("alice", store=MemoryStore(path=path))
    mem1.remember("Prefers annual contracts")

    mem2 = UserMemory("alice", store=MemoryStore(path=path))
    results = mem2.recall("contracts")
    assert len(results) == 1


def test_agent_memory_scoped_by_agent_id(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    research_bot = AgentMemory("research-bot", store=store)
    coding_bot = AgentMemory("coding-bot", store=store)

    research_bot.remember("Found a relevant paper on RAG")
    coding_bot.remember("Refactored the retrieval module")

    assert len(research_bot.recall()) == 1
    assert len(coding_bot.recall()) == 1
    assert "paper" in research_bot.recall()[0].content


def test_organization_memory_shared_across_users(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    org_mem = OrganizationMemory("acme", store=store)
    org_mem.remember("Standard payment terms: net 30")

    same_org_again = OrganizationMemory("acme", store=store)
    results = same_org_again.recall("payment terms")
    assert len(results) == 1


def test_forget_via_tier_wrapper(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    mem = UserMemory("alice", store=store)
    entry_id = mem.remember("Temporary preference")
    assert mem.forget(entry_id) is True
    assert mem.recall() == []

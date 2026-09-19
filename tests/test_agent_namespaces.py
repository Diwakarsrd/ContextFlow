from contextflow.memory.store import MemoryStore
from contextflow.memory.agent import AgentMemory

def test_phase11_agent_handoff_and_namespaces(tmp_path):
    store = MemoryStore(path=str(tmp_path / "memory.db"))
    
    research_agent = AgentMemory("research_agent_01", store)
    coder_agent = AgentMemory("coding_agent_01", store)
    
    # 1. Research agent discovers a private fact
    fact_id = research_agent.remember("The API requires bearer tokens.")
    
    # 2. Coder agent cannot see it initially
    assert len(coder_agent.recall()) == 0
    
    # 3. Direct Handoff (Agent to Agent)
    research_agent.handoff_to("coding_agent_01", fact_id)
    coder_memory = coder_agent.recall()
    assert len(coder_memory) == 1
    assert coder_memory[0].content == "The API requires bearer tokens."
    assert coder_memory[0].metadata["_handoff_source"] == fact_id
    
    # 4. Shared global namespace check
    assert len(research_agent.recall_shared()) == 0
    research_agent.publish_shared(fact_id)
    assert len(coder_agent.recall_shared()) == 1

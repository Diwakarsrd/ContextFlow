import os
import time
from contextflow.graph.resolution import RuleBasedEntityResolver
from contextflow.retrieval.expansion import StaticQueryExpander
from contextflow.compiler.compression import ContextCompressor

def run_simulation():
    print("\n=======================================================")
    print(" INITIALIZING CONTEXTFLOW ENTERPRISE SIMULATION...")
    print("=======================================================\n")
    
    # 1. Setup Enterprise Rules (The "Real World" constraints)
    custom_resolver = RuleBasedEntityResolver(
        canonical_map={
            "@acmecorp": "node_acme_corp",
            "acme": "node_acme_corp",
            "acme corporation": "node_acme_corp",
            "john": "node_usr_john_doe",
            "@jdoe": "node_usr_john_doe"
        }
    )
    
    custom_expander = StaticQueryExpander(
        synonym_map={
            "revenue": ["income", "earnings", "profits"],
            "policy": ["handbook", "guidelines", "rules"]
        }
    )

    print(" Injected Enterprise Graph Rules & Query Synonyms")
    print("\n INGESTING DATALAKE (Simulating real corporate data)...")
    
    # Simulate an old document (2 years old) to test Decay
    doc_old = {
        "id": "doc_hr_2024",
        "text": "Acme Corporation Remote Work Policy: Employees must be in the office 5 days a week.",
        "tenant_id": "tenant_acme",
        "timestamp": time.time() - (86400 * 730) # 2 years ago
    }
    
    # Simulate a brand new document from Slack (Today)
    doc_new = {
        "id": "doc_slack_today",
        "text": "@jdoe posted: Hey team! @acmecorp just announced we are fully remote now! Revenue is up!",
        "tenant_id": "tenant_acme",
        "timestamp": time.time() # Today
    }

    print(" Ingested 2024 HR Handbook (Outdated) & Today's Slack Messages (Fresh)")

    print("\n EXECUTING AGENT QUERY: 'What is acme remote policy?'")
    
    query = "What is acme remote policy?"
    
    # Pipeline Step 1: Expansion
    print("\n[Pipeline Step 1: Query Expansion]")
    expanded = custom_expander.expand(query)
    print(f"   Original: '{query}'")
    print(f"   Expanded: {expanded}")
    
    # Pipeline Step 2: Canonicalization
    print("\n[Pipeline Step 2: Entity Canonicalization (Graph)]")
    resolved_entity = custom_resolver.resolve("acme")
    print(f"   Mapped conversational 'acme' -> Graph Node: '{resolved_entity}'")
    resolved_alias = custom_resolver.resolve("@acmecorp")
    print(f"   Mapped Slack slang '@acmecorp' -> Graph Node: '{resolved_alias}'")
    
    # Pipeline Step 3: Decay
    print("\n[Pipeline Step 3: Semantic Time-Decay Memory Application]")
    # In a real system, the vector DB returns distance. Let's assume both matched at ~0.8 confidence
    conf_old = 0.82
    conf_new = 0.81 
    
    decayed_old = ContextCompressor.apply_decay(conf_old, doc_old["timestamp"], half_life_days=30)
    decayed_new = ContextCompressor.apply_decay(conf_new, doc_new["timestamp"], half_life_days=30)
    
    print(f"   Old 2024 Policy Raw Confidence: {conf_old}")
    print(f"   Old 2024 Policy DECAYED Confidence (2 yrs old): {decayed_old:.6f} ⬇️ (Agent ignores this)")
    
    print(f"   New Slack Message Raw Confidence: {conf_new}")
    print(f"   New Slack Message DECAYED Confidence (Today):   {decayed_new:.6f} ⬆️ (Agent reads this!)")
    
    print("\n CONCLUSION:")
    print("A regular RAG system would pull the 2024 policy because it has a technically higher semantic match.")
    print("ContextFlow correctly resolves the slang aliases ('@acmecorp') and mathematically down-ranks the 2-year old policy, ensuring the AI agent gets the right context and replies 'fully remote'.\n")

if __name__ == "__main__":
    run_simulation()

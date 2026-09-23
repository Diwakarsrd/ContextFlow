from contextflow import ContextEngine
from contextflow.core.context import ContextObject


def showcase_langchain_memory_integration():
    print("--- ContextOS + LangChain Enterprise Integration ---")
    
    # 1. Initialize ContextOS
    engine = ContextEngine()

    # 4111 1111 1111 1111 is a mathematically valid Visa test checksum
    raw_corporate_memo = (
        "Project Phoenix is cleared for Q4. The budget is approved. "
        "Contact the lead engineer at alice.smith@enterprise.com and "
        "route expenses to corporate card 4111 1111 1111 1111."
    )
    
    print("\n[System] LangChain Agent intercepts highly sensitive raw corporate data...")
    obj = ContextObject(content=raw_corporate_memo, source="corporate_slack")
    
    print("[System] Ingesting to ContextOS Memory Block...")
    engine.ingest([obj])
    
    print("\n[LangChain Tool] Query: 'Get Project Phoenix routing details'")
    safe_results = engine.retrieve("Project Phoenix")
    
    print("\n[ContextOS Output to LangChain]")
    if safe_results:
        clean_context = safe_results[0].content
        print(f"RAW RETRIEVAL: {clean_context}")
        
        if "[REDACTED:EMAIL]" in clean_context and "[REDACTED:CREDIT_CARD]" in clean_context:
            print("\n[VERIFIED] ContextOS successfully redacted raw PII synchronously via Luhn Matrix.")
            print("[VERIFIED] LangChain logic can now process the text without violating SOC2.")
            
    print("--------------------------------------------------")

if __name__ == '__main__':
    showcase_langchain_memory_integration()

# Benchmarks (WIP)

We believe that claiming a framework is "production-ready" without verifiable measurements is anti-engineering. 

We are actively benchmarking ContextFlow's Context Packs against naive LangChain/LlamaIndex RAG pipelines using the LOCOMO (Long Context Models) evaluation harness.

### Key Metrics Tracked
* **AST Compilation Latency:** Time to compile a Context Pack from 5 data sources. (Target: < 50ms)
* **RBAC Enforcement Overhead:** Penalty added by policy checks. (Current: < 2ms)
* **Hallucination Reductions:** Percentage decrease in hallucinated graph entities when using ContextFlow's RuleBasedEntityResolver vs raw RAG. 

*Reproducible benchmarking hardware and scripts will be published in this document in v0.2.*

# Known Limitations

ContextFlow is evolving rapidly. While the core memory engine is stable, please be aware of the following architectural limitations:

1. **Streaming Context Updates**
   Currently, ContextFlow compiles 'Context Packs' as distinct, immutable payloads per execution cycle. It does not natively handle real-time WebSockets streaming updates *into* a living agent's working memory mid-execution without triggering a re-compilation phase.

2. **Multimodal Embeddings**
   The Entity Resolution and Query Expansion pipelines are heavily optimized for text and structured data (JSON/Markdown). Full multimodal graph mapping (e.g., pulling bounding boxes from PDFs and linking them to text nodes) is currently considered experimental and not covered by SLA.

3. **Vector Distance Drift**
   If you swap embedding models (e.g., from text-embedding-3-small to a local nomic-embed-text) mid-deployment, ContextFlow's 5-Tier Memory index will not automatically mathematically re-align existing vectors. You must currently initiate a manual re-ingestion pipeline.

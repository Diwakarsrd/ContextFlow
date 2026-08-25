# Example: Basic RAG with ContextFlow

The simplest possible ContextFlow use: ingest a folder of docs, ask a
question, get a Context Pack you can paste into any LLM prompt.

## Run it

```bash
cd examples/basic_rag
pip install -e ../..
python main.py ./sample_docs "What is the refund policy?"
```

No Docker, no API keys, no cloud account — this uses the local-first
in-memory backends from `contextflow.storage.local`.

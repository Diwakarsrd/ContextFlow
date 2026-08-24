# Context Tracing / Observability

Every retrieval call can be run with full pipeline tracing: how many
candidates went in and out of routing, permission/tenant filtering,
reranking, and (for a full pack) compilation — plus timing per stage.

```python
results, trace = engine.retrieve_with_trace("payment decisions", limit=10)
pack, trace = engine.context_pack_with_trace("payment decisions")

for stage in trace.stages:
    print(stage.name, stage.count_in, "->", stage.count_out, f"{stage.duration_ms:.1f}ms")
```

## CLI

```bash
contextflow trace "payment decisions"
```

```
╭──────────────── Context Trace ────────────────╮
│ Query: payment decisions                       │
│                                                 │
│ 127 after route  [43.2ms]                      │
│     ↓                                          │
│ 34 after permission_filter (principal=alice)   │
│     ↓                                          │
│ 12 after rerank  [2.1ms]                       │
│     ↓                                          │
│ 5 after limit (limit=5)                        │
│     ↓                                          │
│ 1 after compile (max_tokens=1000)              │
│                                                 │
│ Confidence: 94%                                │
│ Tokens: 1823                                   │
│ Total time: 47.8ms                             │
╰─────────────────────────────────────────────────╯
```

## MCP

- `trace_query(query, limit)` — run a traced search, get the full
  pipeline breakdown back as JSON.
- `explain_context(context_object_id)` — the actual reranker formula
  (base retrieval score + freshness/confidence/trust weighted by the
  reranker's real weights) for one object, not just its raw fields.

## What this does and doesn't do

Traces are recorded in an in-memory ring buffer per `ContextEngine`
instance (`engine.traces`, default capacity 100) so `get_trace(trace_id)`
works shortly after a call — they are **not** persisted, and restarting
the process clears them. For durable historical analysis of retrieval
behavior over time, see the audit log (`governance/audit.py`) instead,
or wire trace recording into your own logging/metrics pipeline —
`trace.to_dict()` is plain JSON.

`retrieve()` and `context_pack()` are unchanged and don't build a trace
at all (near-zero overhead) — tracing is opt-in via
`retrieve_with_trace()` / `context_pack_with_trace()` / the CLI/MCP tools
above.

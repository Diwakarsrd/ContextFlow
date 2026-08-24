# Memory

Five tiers, one shared persistent store (`memory/store.py`):

| Tier | Class | Scope | Persisted? |
|------|-------|-------|-----------|
| L1 Working | `WorkingMemory` | Current task/turn | No — in-process scratch space, cleared explicitly |
| L2 Session | `SessionMemory` | One conversation | Yes |
| L3 User | `UserMemory` | One user, across sessions | Yes |
| L4 Agent | `AgentMemory` | One agent, across tasks | Yes |
| L5 Organization | `OrganizationMemory` | Org-wide | Yes |

```python
from contextflow.memory.user import UserMemory

mem = UserMemory("alice")
mem.remember("Prefers annual contracts")
mem.remember("Based in the EU, needs GDPR compliance")

mem.recall("contracts")   # BM25-ranked
mem.recall()              # most-recent-first
```

## CLI

```bash
contextflow memory remember user alice "Prefers annual contracts"
contextflow memory recall user alice --query "contracts"
```

## MCP

The `remember` and `get_memory` tools expose the same store to any
connected agent, with `scope` (session/user/agent/org) and `scope_id`
as parameters.

## How recall works

Keyword relevance (BM25) if a query is given, most-recent-first
otherwise. All four persisted tiers share one SQLite table, partitioned
by `(scope, scope_id)` — a user and an agent can even share the same
`scope_id` string without colliding, since scope is part of the key.

## What v1 does not do

No consolidation (merging or summarizing related facts over time), no
decay (old facts don't get deprioritized or forgotten automatically), no
importance scoring, no automatic conflict resolution between
contradictory facts ("prefers annual contracts" vs. a later "switched to
monthly"). These need real usage patterns to design well — see
ROADMAP.md Phase 5.

## A bug this uncovered

Building this surfaced a real thread-safety bug: the MCP server runs
tool calls in a worker-thread pool, and a naive SQLite connection isn't
safe across threads. Both `MemoryStore` and `SQLiteMetadataStore` (the
CLI's persistent metadata backend) now handle this correctly — see
`tests/test_sqlite_thread_safety.py` for a regression test that
reproduces the original crash.

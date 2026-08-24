# REST API Reference

Base URL: `http://localhost:8000` (via `contextflow serve`)

All `/v1` routes require `Authorization: Bearer <key>` once API keys are
configured (`contextflow auth create-key`) — see SECURITY.md. There is no
`principal` field in any request body; identity always comes from the
verified key.

## `POST /v1/search`

```json
{ "query": "refund policy", "limit": 10 }
```

Returns a list of `ContextObject` (see `core/context.py`).

## `POST /v1/context-pack`

```json
{ "task": "prepare customer renewal", "entity": "Acme", "max_tokens": 3000 }
```

Returns a `ContextPack` (see `core/context_pack.py`).

## `POST /v1/trace`

```json
{ "query": "payment decisions", "limit": 10 }
```

Runs a search with full pipeline tracing and returns a `ContextTrace` —
candidate counts and timing at each stage (route, permission filter,
tenant filter, rerank, limit). See docs/concepts/tracing.md.

## `POST /v1/memory/remember`

```json
{ "scope": "user", "scope_id": "alice", "fact": "Prefers annual contracts" }
```

Returns `{"id": "<uuid>"}`.

## `POST /v1/memory/recall`

```json
{ "scope": "user", "scope_id": "alice", "query": "contracts", "limit": 10 }
```

Returns a list of memory entries (`id`, `content`, `metadata`,
`created_at`), ranked by keyword relevance if `query` is given, else
most-recent-first. `scope` is one of `session`/`user`/`agent`/`org`. See
docs/concepts/memory.md.

## `GET /health`

Returns `{"status": "ok"}`. No auth required.

## Clients

- Python: use `ContextEngine` directly, or the REST endpoints above from
  any HTTP client.
- TypeScript: `sdk/typescript` — see its README for usage. Tested against
  a real running instance of this API, not a mock.

Full request/response schemas: `src/contextflow/api/schemas/requests.py`
and `src/contextflow/core/context_pack.py`.

# Example: GitHub Coding Agent Context

Shows how a coding agent would use ContextFlow's MCP server to pull
relevant issues/PRs before making a change, instead of relying on raw
grep or a fixed context window.

## Run it

```bash
cd examples/github_agent
export GITHUB_TOKEN=ghp_...
docker compose -f ../../docker-compose.yml up -d postgres qdrant
contextflow mcp
```

Then point any MCP-compatible agent (Claude, Cursor, ...) at the running
MCP server and call `get_context_pack(task="fix the login bug")`.

## Status

The GitHub connector's `fetch()` is a stub in v0.1 (see
`src/contextflow/connectors/github/connector.py`) — implementing it against
the GitHub REST/GraphQL API is a great first contribution. See
`CONTRIBUTING.md`.

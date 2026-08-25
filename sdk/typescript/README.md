# @contextflow/sdk

TypeScript client for the ContextFlow REST API. Talks to a running
`contextflow serve` instance — see the root
[getting_started.md](../../docs/getting_started.md) for how to run one.

## Install

Not yet published — build locally:

```bash
cd sdk/typescript
npm install
npm run build
```

## Usage

```ts
import { ContextEngine, ContextFlowError } from "@contextflow/sdk";

const engine = new ContextEngine({
  baseUrl: "http://localhost:8000",
  apiKey: "sk_...", // from `contextflow auth create-key` — omit only
                     // against a server running in open/local-dev mode
});

const results = await engine.retrieve("payment decisions", { limit: 5 });

const pack = await engine.contextPack("prepare for customer renewal", {
  entity: "Acme",
  maxTokens: 1000,
});

const trace = await engine.trace("payment decisions");
console.log(trace.stages.map((s) => `${s.name}: ${s.count_in} -> ${s.count_out}`));

await engine.remember("user", "alice", "Prefers annual contracts");
const memories = await engine.recall("user", "alice", { query: "contracts" });

try {
  await engine.retrieve("x");
} catch (err) {
  if (err instanceof ContextFlowError) {
    console.error(err.status, err.message); // 401, 429, etc.
  }
}
```

## What this does and doesn't cover

Covers everything the REST API exposes: `retrieve`, `contextPack`,
`trace`, `remember`/`recall`. It does **not** cover ingestion — there is
no REST ingest endpoint yet (use the Python SDK/CLI or a connector to
get data in; see ROADMAP.md). It also doesn't wrap the MCP server —
that's a separate protocol or use the Python `mcp` server directly.

## Testing

```bash
npm test
```

This spins up a real `contextflow serve` (Python) instance as a
subprocess and runs every test against real HTTP calls to it — including
real auth enforcement (401 with no/bad key) and a real memory
remember/recall round trip. Nothing here is mocked; if the SDK's request
shapes drift from the actual API, these tests fail for a real reason.
Requires Python + the `contextflow` package installed and on `PATH`
(`pip install -e .` from the repo root).

# Security Self-Review (v0.1)

This is a self-review by the person/team who wrote the auth and
governance code, not an independent audit. Treat it as a map of what's
been thought about and what hasn't, not a certification. If you're
considering production use, get an actual third-party review first.

## What's in scope for this review

`src/contextflow/auth/`, `src/contextflow/governance/`, and how they're
wired into `src/contextflow/api/` and `src/contextflow/mcp/`.

## Threat model (what this defends against)

- An unauthenticated network caller trying to read data via the REST API
  or MCP-over-HTTP.
- A caller with a valid key for principal A trying to read data scoped to
  principal B or a role they don't hold.
- A caller trying to claim a false identity by manipulating request
  content (the specific bug this review's changes fixed — see below).
- Naive brute-force guessing of API keys.
- A leaked `.contextflow/api_keys.json` file being directly usable to
  authenticate.

## What's NOT in scope / NOT defended against

- **Multi-instance deployments.** The rate limiter is in-memory,
  per-process. Behind a load balancer with multiple API replicas, an
  attacker can distribute guesses across instances and the limiter won't
  see the full picture. Fix: a shared store (Redis) — not built.
- **Timing attacks on the rate limiter's IP-based bucketing itself**, or
  on `PolicyEngine`/`APIKeyStore` dict lookups. Key comparison goes
  through a hash-table lookup on a SHA-256 digest rather than a naive
  `==` on the secret, which avoids the most textbook timing
  side-channel, but this hasn't been tested against a real timing attack
  and dict-lookup timing characteristics haven't been analyzed.
- **Transport security.** Nothing here does TLS termination — that's
  assumed to be handled by whatever sits in front of this (a reverse
  proxy, load balancer, etc.) in any real deployment. Running `contextflow
  serve` directly on the open internet without TLS in front of it would
  send API keys in plaintext.
- **Key scoping.** A key grants everything its principal can see — there's
  no way to mint a read-only or narrowly-scoped key.
- **ABAC / fine-grained conditions.** Access control is allow-list or
  role-membership only. There's no "principal X can read documents from
  source Y created after date Z" style condition.
- **PII detection is not enforced anywhere automatically.** It's a
  callable utility (`governance/pii.py`). Nothing stops PII from being
  ingested, stored, or returned in a Context Pack unless something
  upstream calls `redact_pii()` explicitly.
- **The MCP stdio transport has no authentication by design** — this is
  intentional (see `auth/mcp_token_verifier.py`'s docstring: the trust
  boundary is process-spawn permission, same as any local CLI tool), but
  it means anything that can start the `contextflow mcp` process gets full
  access. Don't run it as a shared/multi-tenant service over stdio.
- **Dependency security.** No SBOM, no automated dependency vulnerability
  scanning beyond Dependabot's default update PRs. No fuzzing of any
  input-parsing code (connectors, request schemas).
- **Denial of service beyond the rate limiter.** No request size limits,
  no timeout enforcement beyond what FastAPI/httpx default to, no
  protection against a maliciously large ingestion job.

## Specific things fixed during development (for transparency)

- **Principal spoofing (fixed):** the REST API originally accepted a
  client-supplied `principal` field in `SearchRequest`/`ContextPackRequest`.
  Any caller could claim to be anyone and see their permission-scoped
  data. Fixed by deriving principal exclusively from the verified API
  key server-side; the field no longer exists in the request schema.
- **Plaintext key storage (fixed):** `APIKeyStore` originally stored keys
  in plaintext in `.contextflow/api_keys.json`. A leaked file was
  immediately usable. Fixed by storing only a SHA-256 hash; the plaintext
  key is shown once at creation and cannot be recovered.
- **SQL injection in the PostgreSQL connector (fixed and live-verified):**
  table/column identifiers can't be parameterized in SQL, so they're
  validated against a strict allow-list regex before being interpolated;
  the `LIMIT` value is a real bound parameter. See
  `connectors/postgres/connector.py: _validate_identifier`. Proven both
  by unit test and by a live test that attempts a malicious identifier
  against a real running PostgreSQL instance
  (`tests/test_postgres_live.py::test_rejects_unsafe_table_identifier_even_with_live_db`).

## How to report a problem

See `SECURITY.md`. Please report privately rather than opening a public
issue for anything that looks like an actual vulnerability, not just a
documented limitation above.

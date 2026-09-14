# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, email **security@contextflow.dev** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact

We aim to acknowledge reports within 48 hours and to ship a fix or
mitigation plan within 14 days for confirmed issues.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   |         |
| < 0.1   |         |

## Scope notes

ContextFlow retrieves and compiles data from connected sources on behalf of
an agent. If you find a way for permission-aware retrieval to leak content
a caller shouldn't have access to, that is treated as a critical
vulnerability — please report it privately.

## Authentication

The REST API and MCP-over-HTTP share one API key store
(`contextflow auth create-key <principal>`). With no keys configured, both
run in **open mode** — full access, no credential required — which is
appropriate for local development only and logs an explicit warning when
active. Configure keys (`$CONTEXTOS_API_KEYS` or the generated
`.contextflow/api_keys.json`) before exposing either surface beyond
localhost.

Keys are hashed at rest (never stored in plaintext), can carry an
optional expiry, and can be revoked (`contextflow auth revoke-key`).
There's no per-key scope restriction yet (tracked in ROADMAP.md Phase 7)
— a key grants everything its principal can see. Treat a leaked key as
equivalent to a leaked password for that principal.

Repeated failed auth attempts from one client are rate-limited
(`auth/rate_limit.py`) — in-memory and per-process, so it doesn't
coordinate across multiple replicas behind a load balancer yet.

See [docs/security_review.md](docs/security_review.md) for a full,
honest self-assessment of what is and isn't covered — it is not a
substitute for an independent audit.

## Governance

RBAC (roles + explicit allow-lists), tenant isolation, pattern-based PII
detection, and queryable audit logging all ship in v0.1 — see
[docs/concepts/governance.md](docs/concepts/governance.md). None of this
has had an external security review. If you find a way to bypass
permission/role/tenant filtering, or a PII pattern gap that matters for
your use case, please report it privately per the process above.

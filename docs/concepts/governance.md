# Governance

## Access control

Two independent mechanisms, both enforced *before* ranking:

- **Explicit allow-list**: `ContextObject.permissions = ["alice"]` — only
  those principals see it.
- **Role-based**: `ContextObject.allowed_roles = ["finance"]` plus
  `contextflow auth assign-role alice finance` — anyone holding the role sees it.

An object with neither set is unrestricted (visible to everyone).

```python
from contextflow.governance.policies import PolicyEngine, RoleStore

roles = RoleStore()               # persisted to .contextflow/roles.json
roles.assign("alice", "finance")

engine = ContextEngine(policy_engine=PolicyEngine(roles))
engine.retrieve("Q4 numbers", principal="alice")   # sees finance-gated content
engine.retrieve("Q4 numbers", principal="bob")     # doesn't
```

## Tenant isolation

```python
ContextObject(content="...", tenant_id="acme")
engine.retrieve("query", tenant_id="acme")   # only "acme" + untenanted content
```

Untenanted content (`tenant_id=None`) is treated as shared/global and
returned regardless of which tenant is querying.

## PII / secret detection

```python
from contextflow.governance.pii import contains_pii, find_pii, redact_pii

redact_pii("Contact alice@example.com or call 555-123-4567")
# "Contact [REDACTED:EMAIL] or call [REDACTED:PHONE]"
```

Pattern-based: emails, phone numbers, SSNs, Luhn-validated credit card
numbers, AWS access keys, generic API-key-shaped secrets. It is **not**
wired into the ingestion pipeline automatically — call it explicitly, or
add a connector-level hook, until a real ingestion-time policy exists
(see ROADMAP.md). It will also miss unstructured PII (names, addresses in
prose) — a model-based (NER) second pass is a good contribution.

## Audit log

```bash
contextflow audit query --principal alice
contextflow audit query --action search
```

Every REST API `/v1/search` and `/v1/context-pack` call is recorded with
principal, action, and query/task. Append-only JSONL at
`.contextflow/audit.log`.

## What's still missing

Real ABAC (conditions beyond role membership), key rotation/expiry,
per-key scopes, data masking as an automatic ingestion policy, and a
third-party security review of the auth code. See ROADMAP.md Phase 7.

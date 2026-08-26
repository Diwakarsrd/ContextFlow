"""API key store shared by the REST API and the MCP-over-HTTP server.

Keys map to a *principal* — the identity used by permission-aware
retrieval (`ContextObject.permissions`, `governance/permissions.py`).
Principal always comes from a verified credential, never from request
content (see `fastapi_deps.py`'s docstring for the spoofing bug this
closes).

Security notes (see docs/security_review.md for the full write-up):

- Keys are stored **hashed** (SHA-256), never in plaintext, in both the
  JSON file and in memory after creation. `create_key()` returns the
  plaintext key exactly once — the same UX as GitHub/Stripe personal
  access tokens — and it cannot be recovered afterward, only revoked
  and reissued.
- Lookup is a hash-table lookup on the hashed key, not a direct
  character-by-character comparison of secrets, which avoids the
  classic `==`-on-secrets timing side-channel.
- Keys support optional expiry (`expires_at`) and revocation.

Configuration (checked in order):

1. `$CONTEXTOS_API_KEYS` — comma-separated `key:principal` pairs, meant
   for prod/CI (e.g. injected as a secret): `sk_abc123:alice,sk_def456:bob`
   (hashed in memory immediately on load; never written back to disk)
2. `.contextflow/api_keys.json` — written by `contextflow auth create-key`,
   stores only hashes: `{"<sha256-hex>": {"principal": "alice", "expires_at": null}}`

If neither is configured, the store is empty and callers fall back to
**open mode** (see `auth/fastapi_deps.py` / `auth/mcp_token_verifier.py`)
— appropriate for local single-user development only. Anything reachable
beyond localhost must configure real keys.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class APIKeyStore:
    def __init__(self, keys: dict[str, str] | None = None) -> None:
        """`keys` maps *plaintext* key -> principal for convenient
        construction in tests/config; it's hashed immediately and the
        plaintext is not retained."""
        self._entries: dict[str, dict[str, Any]] = {}
        for plaintext, principal in (keys or {}).items():
            self._entries[_hash_key(plaintext)] = {"principal": principal, "expires_at": None}

    @classmethod
    def from_env_and_file(cls, path: str = ".contextflow/api_keys.json") -> APIKeyStore:
        store = cls()

        file_path = Path(path)
        if file_path.exists():
            store._entries.update(json.loads(file_path.read_text() or "{}"))

        env_value = os.environ.get("CONTEXTOS_API_KEYS", "")
        for pair in env_value.split(","):
            pair = pair.strip()
            if not pair:
                continue
            key, _, principal = pair.partition(":")
            if key and principal:
                store._entries[_hash_key(key)] = {"principal": principal, "expires_at": None}

        return store

    def verify(self, key: str) -> str | None:
        """Return the principal for a valid, non-expired key, or None."""
        entry = self._entries.get(_hash_key(key))
        if entry is None:
            return None
        expires_at = entry.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            return None
        return entry["principal"]

    def is_configured(self) -> bool:
        return bool(self._entries)

    def create_key(
        self,
        principal: str,
        path: str = ".contextflow/api_keys.json",
        expires_in_days: int | None = None,
    ) -> str:
        """Generate a new key for `principal`, persist only its hash to
        `path`, and return the plaintext key. This is the only moment the
        plaintext key exists — store it now, it cannot be recovered later.
        """
        key = f"sk_{secrets.token_hex(24)}"
        expires_at = time.time() + expires_in_days * 86400 if expires_in_days else None
        entry = {"principal": principal, "expires_at": expires_at}
        self._entries[_hash_key(key)] = entry

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if file_path.exists():
            existing = json.loads(file_path.read_text() or "{}")
        existing[_hash_key(key)] = entry
        file_path.write_text(json.dumps(existing, indent=2))

        return key

    def revoke_key(self, key: str, path: str = ".contextflow/api_keys.json") -> bool:
        """Revoke a key by its plaintext value. Returns True if a key was
        found and removed."""
        key_hash = _hash_key(key)
        removed = self._entries.pop(key_hash, None) is not None

        file_path = Path(path)
        if file_path.exists():
            existing = json.loads(file_path.read_text() or "{}")
            if existing.pop(key_hash, None) is not None:
                file_path.write_text(json.dumps(existing, indent=2))
                removed = True

        return removed

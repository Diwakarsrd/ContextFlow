"""FastAPI auth dependency.

The principal used for permission-aware retrieval always comes from
here — never from request body content — closing the spoofing gap where
v0.1's `SearchRequest.principal` let any caller claim to be anyone.

Also rate-limits repeated failed attempts per client IP (see
`auth/rate_limit.py` for what this does and doesn't protect against).
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request

from contextflow.auth.api_keys import APIKeyStore
from contextflow.auth.rate_limit import RateLimiter

logger = logging.getLogger("contextflow.auth")
_warned_open_mode = False


def require_principal(request: Request, authorization: str | None = Header(default=None)) -> str:
    store: APIKeyStore = request.app.state.api_key_store
    rate_limiter: RateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"

    if not store.is_configured():
        global _warned_open_mode
        if not _warned_open_mode:
            logger.warning(
                "CONTEXTOS_API_KEYS is not set — the API is running in open mode "
                "(no authentication, full access as 'local-admin'). This is only "
                "appropriate for local development. Run `contextflow auth create-key` "
                "before exposing this beyond localhost."
            )
            _warned_open_mode = True
        return "local-admin"

    if rate_limiter.is_blocked(client_ip):
        raise HTTPException(
            status_code=429, detail="Too many failed authentication attempts. Try again later."
        )

    if not authorization or not authorization.startswith("Bearer "):
        rate_limiter.record_failure(client_ip)
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    principal = store.verify(token)
    if principal is None:
        rate_limiter.record_failure(client_ip)
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    rate_limiter.record_success(client_ip)
    return principal

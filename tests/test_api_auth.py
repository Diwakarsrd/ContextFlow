from fastapi.testclient import TestClient

from contextflow.api.app import create_app
from contextflow.auth.api_keys import APIKeyStore
from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine


def _engine_with_data() -> ContextEngine:
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(content="public revenue numbers", source="test"),
            ContextObject(
                content="private salary data revenue", source="test", permissions=["alice"]
            ),
        ]
    )
    return engine


def test_open_mode_allows_requests_with_no_key():
    # No keys configured at all -> open/dev mode, not locked out.
    app = create_app(engine=_engine_with_data(), api_key_store=APIKeyStore())
    client = TestClient(app)
    resp = client.post("/v1/search", json={"query": "revenue"})
    assert resp.status_code == 200


def test_configured_keys_reject_missing_or_bad_credentials():
    store = APIKeyStore({"sk_good": "alice"})
    app = create_app(engine=_engine_with_data(), api_key_store=store)
    client = TestClient(app)

    resp = client.post("/v1/search", json={"query": "revenue"})
    assert resp.status_code == 401

    resp = client.post(
        "/v1/search",
        json={"query": "revenue"},
        headers={"Authorization": "Bearer sk_wrong"},
    )
    assert resp.status_code == 401


def test_valid_key_grants_access_scoped_to_its_own_principal():
    store = APIKeyStore({"sk_alice": "alice", "sk_bob": "bob"})
    app = create_app(engine=_engine_with_data(), api_key_store=store)
    client = TestClient(app)

    # alice's key can see the object scoped to "alice"
    resp = client.post(
        "/v1/search",
        json={"query": "revenue", "limit": 10},
        headers={"Authorization": "Bearer sk_alice"},
    )
    assert resp.status_code == 200
    contents = [r["content"] for r in resp.json()]
    assert any("salary" in c for c in contents)

    # bob's key cannot -- and there's no `principal` field in the request
    # body to spoof around this; identity comes only from the API key.
    resp = client.post(
        "/v1/search",
        json={"query": "revenue", "limit": 10},
        headers={"Authorization": "Bearer sk_bob"},
    )
    assert resp.status_code == 200
    contents = [r["content"] for r in resp.json()]
    assert not any("salary" in c for c in contents)


def test_search_request_schema_has_no_principal_field():
    from contextflow.api.schemas.requests import SearchRequest

    assert "principal" not in SearchRequest.model_fields


def test_rate_limiter_blocks_repeated_failed_attempts():
    from contextflow.auth.rate_limit import RateLimiter

    store = APIKeyStore({"sk_good": "alice"})
    limiter = RateLimiter(max_attempts=3, window_seconds=60)
    app = create_app(engine=_engine_with_data(), api_key_store=store, rate_limiter=limiter)
    client = TestClient(app)

    for _ in range(3):
        resp = client.post(
            "/v1/search",
            json={"query": "revenue"},
            headers={"Authorization": "Bearer sk_wrong"},
        )
        assert resp.status_code == 401

    # Fourth attempt is blocked outright, even with the correct key now.
    resp = client.post(
        "/v1/search",
        json={"query": "revenue"},
        headers={"Authorization": "Bearer sk_good"},
    )
    assert resp.status_code == 429

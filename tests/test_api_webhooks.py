import pytest
from fastapi.testclient import TestClient

from contextflow.api.app import app
from contextflow.governance.policies import PolicyEngine
from contextflow.auth.api_keys import APIKeyStore

@pytest.fixture
def client():
    # Setup test policy engine and user with an API key
    app.state.engine.policy_engine = PolicyEngine()
    store = APIKeyStore(keys={"sk_test_webhook123": "webhook_service"})
    app.state.api_key_store = store
    
    with TestClient(app) as c:
        yield c

def test_phase8_webhook_ingestion(client):
    headers = {"Authorization": "Bearer sk_test_webhook123"}
    
    payload = {
        "source": "slack_webhook",
        "content": "URGENT: Database migration failed on US-East. John's email is john.doe@acme.com",
        "metadata": {"channel": "#devops"},
        "tenant_id": "org_123"
    }
    
    # 1. Post to the real-time ingest route
    resp = client.post("/v1/webhooks/ingest", headers=headers, json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["indexed_chunks"] >= 1
    
    # 2. Verify the engine actually indexed it and applied PII redaction synchronously
    search_resp = client.post("/v1/search", headers=headers, json={"query": "database migration US-East"})
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) >= 1
    assert "john.doe@acme.com" not in results[0]["content"]
    assert "[REDACTED:EMAIL]" in results[0]["content"]
    assert results[0]["source"] == "slack_webhook"

import pytest
from fastapi.testclient import TestClient

from contextflow.api.app import app
from contextflow.governance.policies import PolicyEngine
from contextflow.auth.api_keys import APIKeyStore


@pytest.fixture
def client():
    # Setup test policy engine and user with an API key
    app.state.engine.policy_engine = PolicyEngine()
    store = APIKeyStore(keys={"sk_test_admin123": "admin_user"})
    app.state.api_key_store = store

    with TestClient(app) as c:
        yield c


def test_governance_api_rbac_flow(client):
    headers = {"Authorization": "Bearer sk_test_admin123"}

    # 1. Assign role
    resp = client.post(
        "/v1/governance/roles/assign",
        headers=headers,
        json={"principal": "user_a", "role": "engineering"},
    )
    assert resp.status_code == 200
    assert "engineering" in resp.json()["roles"]

    # 2. Get roles
    resp = client.get("/v1/governance/roles/user_a", headers=headers)
    assert resp.status_code == 200
    assert "engineering" in resp.json()["roles"]

    # 3. Revoke role
    resp = client.post(
        "/v1/governance/roles/revoke",
        headers=headers,
        json={"principal": "user_a", "role": "engineering"},
    )
    assert resp.status_code == 200
    assert "engineering" not in resp.json()["roles"]

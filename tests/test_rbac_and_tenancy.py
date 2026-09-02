from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine
from contextflow.governance.policies import PolicyEngine, RoleStore


def test_role_store_assign_and_revoke(tmp_path):
    store = RoleStore(path=str(tmp_path / "roles.json"))
    store.assign("alice", "admin")
    assert store.roles_for("alice") == ["admin"]

    store.revoke("alice", "admin")
    assert store.roles_for("alice") == []


def test_policy_engine_grants_access_via_role(tmp_path):
    role_store = RoleStore(path=str(tmp_path / "roles.json"))
    role_store.assign("alice", "finance")
    policy = PolicyEngine(role_store)

    assert policy.can_read("alice", allowed_roles=["finance"], permissions=[])
    assert not policy.can_read("bob", allowed_roles=["finance"], permissions=[])


def test_policy_engine_still_honors_explicit_permissions(tmp_path):
    policy = PolicyEngine(RoleStore(path=str(tmp_path / "roles.json")))
    assert policy.can_read("bob", allowed_roles=["finance"], permissions=["bob"])


def test_unrestricted_object_visible_to_everyone(tmp_path):
    policy = PolicyEngine(RoleStore(path=str(tmp_path / "roles.json")))
    assert policy.can_read("anyone", allowed_roles=[], permissions=[])


def test_engine_retrieve_uses_policy_engine_for_role_based_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    role_store = RoleStore()
    role_store.assign("alice", "finance")
    policy = PolicyEngine(role_store)

    engine = ContextEngine(policy_engine=policy)
    engine.ingest(
        [
            ContextObject(content="quarterly revenue figures", source="t", allowed_roles=["finance"]),
        ]
    )

    alice_results = engine.retrieve("revenue", principal="alice")
    assert len(alice_results) == 1

    bob_results = engine.retrieve("revenue", principal="bob")
    assert len(bob_results) == 0


def test_tenant_isolation():
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(content="acme corp revenue data", source="t", tenant_id="acme"),
            ContextObject(content="widgets inc revenue data", source="t", tenant_id="widgets"),
            ContextObject(content="shared public revenue benchmark", source="t"),
        ]
    )

    acme_results = engine.retrieve("revenue", tenant_id="acme", limit=10)
    contents = [o.content for o in acme_results]
    assert any("acme" in c for c in contents)
    assert not any("widgets inc" in c for c in contents)
    assert any("shared public" in c for c in contents)  # untenanted content is global

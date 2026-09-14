import json

from contextflow.auth.api_keys import APIKeyStore, _hash_key


def test_empty_store_is_not_configured():
    store = APIKeyStore()
    assert not store.is_configured()
    assert store.verify("anything") is None


def test_create_key_persists_hash_not_plaintext(tmp_path):
    path = tmp_path / "api_keys.json"
    store = APIKeyStore()
    key = store.create_key("alice", path=str(path))

    assert store.verify(key) == "alice"
    assert store.is_configured()

    persisted = json.loads(path.read_text())
    # The plaintext key must never appear in the persisted file.
    assert key not in json.dumps(persisted)
    assert persisted[_hash_key(key)]["principal"] == "alice"


def test_from_env_and_file_merges_both_sources(tmp_path, monkeypatch):
    path = tmp_path / "api_keys.json"
    path.write_text(
        json.dumps({_hash_key("key-from-file"): {"principal": "bob", "expires_at": None}})
    )
    monkeypatch.setenv("CONTEXTOS_API_KEYS", "key-from-env:carol")
    monkeypatch.chdir(tmp_path)

    store = APIKeyStore.from_env_and_file(path=str(path))
    assert store.verify("key-from-file") == "bob"
    assert store.verify("key-from-env") == "carol"


def test_expired_key_is_rejected(tmp_path):
    path = tmp_path / "api_keys.json"
    store = APIKeyStore()
    key = store.create_key("alice", path=str(path), expires_in_days=-1)  # already expired
    assert store.verify(key) is None


def test_unexpired_key_still_works(tmp_path):
    path = tmp_path / "api_keys.json"
    store = APIKeyStore()
    key = store.create_key("alice", path=str(path), expires_in_days=30)
    assert store.verify(key) == "alice"


def test_revoke_key_removes_access(tmp_path):
    path = tmp_path / "api_keys.json"
    store = APIKeyStore()
    key = store.create_key("alice", path=str(path))
    assert store.verify(key) == "alice"

    revoked = store.revoke_key(key, path=str(path))
    assert revoked is True
    assert store.verify(key) is None

    # A second revoke of the same (now-gone) key is a no-op, not an error.
    assert store.revoke_key(key, path=str(path)) is False


def test_reloading_store_after_revoke_reflects_removal(tmp_path):
    path = tmp_path / "api_keys.json"
    store = APIKeyStore()
    key = store.create_key("alice", path=str(path))
    store.revoke_key(key, path=str(path))

    reloaded = APIKeyStore.from_env_and_file(path=str(path))
    assert reloaded.verify(key) is None

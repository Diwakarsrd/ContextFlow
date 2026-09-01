from contextflow.governance.audit import AuditLog


def test_record_and_query_roundtrip(tmp_path):
    log = AuditLog(path=str(tmp_path / "audit.log"))
    log.record("alice", "search", {"query": "revenue"})
    log.record("bob", "search", {"query": "salaries"})
    log.record("alice", "context_pack", {"task": "prepare review"})

    all_entries = log.query()
    assert len(all_entries) == 3

    alice_entries = log.query(principal="alice")
    assert len(alice_entries) == 2
    assert all(e["principal"] == "alice" for e in alice_entries)

    search_entries = log.query(action="search")
    assert len(search_entries) == 2


def test_query_since_filters_by_time(tmp_path):
    log = AuditLog(path=str(tmp_path / "audit.log"))
    log.record("alice", "search", {"query": "revenue"})

    assert len(log.query(since=0)) == 1
    import time

    assert len(log.query(since=time.time() + 3600)) == 0


def test_query_empty_log_returns_empty_list(tmp_path):
    log = AuditLog(path=str(tmp_path / "does_not_exist.log"))
    assert log.query() == []

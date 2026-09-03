from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine
from contextflow.observability.trace import ContextTrace, TraceRecorder


def test_retrieve_with_trace_records_stages():
    engine = ContextEngine()
    engine.ingest([ContextObject(content="revenue dropped due to churn", source="t")])

    results, trace = engine.retrieve_with_trace("revenue", limit=5)
    assert len(results) == 1
    stage_names = [s.name for s in trace.stages]
    assert "route" in stage_names
    assert "rerank" in stage_names
    assert "limit" in stage_names
    assert trace.total_duration_ms >= 0


def test_trace_reflects_permission_filtering_reducing_candidates():
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(content="public revenue numbers", source="t"),
            ContextObject(content="private revenue figures", source="t", permissions=["alice"]),
        ]
    )

    _, trace = engine.retrieve_with_trace("revenue", principal="bob", limit=10)
    perm_stage = next(s for s in trace.stages if s.name == "permission_filter")
    assert perm_stage.count_in == 2
    assert perm_stage.count_out == 1  # bob can't see alice's object


def test_trace_reflects_tenant_filtering():
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(content="acme revenue data", source="t", tenant_id="acme"),
            ContextObject(content="widgets revenue data", source="t", tenant_id="widgets"),
        ]
    )

    _, trace = engine.retrieve_with_trace("revenue", tenant_id="acme", limit=10)
    tenant_stage = next(s for s in trace.stages if s.name == "tenant_filter")
    assert tenant_stage.count_in == 2
    assert tenant_stage.count_out == 1


def test_context_pack_with_trace_includes_compile_stage_and_final_metrics():
    engine = ContextEngine()
    engine.ingest([ContextObject(content="Stripe was selected for payments", source="t")])

    pack, trace = engine.context_pack_with_trace("payments", max_tokens=500)
    assert any(s.name == "compile" for s in trace.stages)
    assert trace.final_confidence == pack.confidence
    assert trace.final_tokens == pack.tokens_used


def test_retrieve_without_trace_does_not_record_to_ring_buffer():
    engine = ContextEngine()
    engine.ingest([ContextObject(content="hello", source="t")])
    engine.retrieve("hello")
    assert engine.traces.recent() == []


def test_retrieve_with_trace_is_recorded_and_retrievable():
    engine = ContextEngine()
    engine.ingest([ContextObject(content="hello", source="t")])
    _, trace = engine.retrieve_with_trace("hello")

    fetched = engine.get_trace(trace.id)
    assert fetched is not None
    assert fetched.id == trace.id


def test_trace_recorder_ring_buffer_respects_capacity():
    recorder = TraceRecorder(capacity=3)
    for i in range(5):
        recorder.record(ContextTrace(query=f"q{i}"))

    recent = recorder.recent(limit=10)
    assert len(recent) == 3
    # Most recent first, and only the last 3 survive.
    assert [t.query for t in recent] == ["q4", "q3", "q2"]


def test_trace_to_dict_is_json_serializable():
    import json

    trace = ContextTrace(query="test")
    trace.add_stage("route", count_in=0, count_out=5, duration_ms=1.234, foo="bar")
    trace.final_confidence = 0.9
    trace.final_tokens = 100

    serialized = json.dumps(trace.to_dict())
    parsed = json.loads(serialized)
    assert parsed["query"] == "test"
    assert parsed["stages"][0]["details"] == {"foo": "bar"}

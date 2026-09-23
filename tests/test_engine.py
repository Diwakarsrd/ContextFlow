from contextflow.core.context import ContextObject
from contextflow.engine import ContextEngine


def test_ingest_and_retrieve():
    engine = ContextEngine()
    objects = [
        ContextObject(content="The quarterly revenue dropped due to churn.", source="test"),
        ContextObject(content="Our roadmap includes a new pricing page.", source="test"),
    ]
    indexed = engine.ingest(objects)
    assert indexed == 2

    results = engine.retrieve("Why did revenue drop?", limit=5)
    assert len(results) > 0
    assert any("revenue" in obj.content.lower() for obj in results)


def test_context_pack_respects_token_budget():
    engine = ContextEngine()
    long_text = "revenue " * 2000
    engine.ingest([ContextObject(content=long_text, source="test")])

    pack = engine.context_pack(task="revenue", max_tokens=50)
    assert pack.tokens_used is not None
    assert pack.tokens_used <= 50


def test_permission_filtering():
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(content="public revenue numbers", source="test"),
            ContextObject(
                content="private salary data revenue", source="test", permissions=["alice"]
            ),
        ]
    )
    results = engine.retrieve("revenue", limit=10, principal="bob")
    assert all("salary" not in obj.content for obj in results)


def test_retrieval_scores_do_not_leak_into_stored_objects_or_later_queries():
    engine = ContextEngine()
    engine.ingest(
        [
            ContextObject(id="pay", content="Stripe was chosen as the payment processor.", source="t"),
            ContextObject(id="hire", content="We hired two backend engineers in May.", source="t"),
        ]
    )
    first = engine.retrieve("payment processor", limit=2)
    assert all("_retrieval_score" in obj.metadata for obj in first)
    # The stored objects must stay clean: a score from one query must not
    # carry over and influence how the next query ranks them.
    for oid in ("pay", "hire"):
        stored = engine.metadata_store.get(oid)
        assert stored is not None
        assert not any(k.endswith("_score") for k in stored.metadata)

    second = engine.retrieve("backend engineers hired", limit=2)
    assert second[0].id == "hire"
    assert 0.0 < second[0].metadata["_retrieval_score"] <= 1.0


def test_keyword_tokenizer_strips_punctuation_and_stopwords_but_keeps_unicode():
    from contextflow.retrieval.keyword import tokenize

    assert tokenize("What did Caroline do yesterday?") == ["caroline", "yesterday"]
    assert tokenize("Zürich café, GDPR-2024") == ["zürich", "café", "gdpr", "2024"]
    assert tokenize("Acme's payments status access") == ["acme", "payment", "status", "access"]

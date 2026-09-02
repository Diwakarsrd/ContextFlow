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

from contextflow.core.context import ContextObject
from contextflow.engine import local_workspace


def test_local_workspace_persists_across_engine_instances(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    engine1 = local_workspace(".contextflow")
    engine1.ingest([ContextObject(content="Stripe handles our payments.", source="test")])

    # A brand-new ContextEngine instance, backed by the same on-disk
    # workspace, should see what the first instance ingested — this is
    # the CLI's ingest-then-search-in-a-separate-process path.
    engine2 = local_workspace(".contextflow")
    results = engine2.retrieve("payments")
    assert any("Stripe" in obj.content for obj in results)

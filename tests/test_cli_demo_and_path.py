from typer.testing import CliRunner

from contextflow.cli.main import app

runner = CliRunner()


def test_demo_command_runs_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "Ingested" in result.output
    assert "Context Pack" in result.output
    assert (tmp_path / "contextflow-demo" / "docs" / "architecture.md").exists()
    assert (tmp_path / "contextflow-demo" / ".contextflow").exists()


def test_ingest_and_search_respect_custom_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "note.md").write_text("Stripe handles our payments processing.")

    result = runner.invoke(app, ["ingest", str(docs_dir), "--path", "custom_ws"])
    assert result.exit_code == 0
    assert (tmp_path / "custom_ws").exists()
    assert not (tmp_path / ".contextflow").exists()  # default path untouched

    result = runner.invoke(app, ["search", "payments", "--path", "custom_ws"])
    assert result.exit_code == 0
    assert "Stripe" in result.output


def test_search_with_wrong_path_finds_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "note.md").write_text("Stripe handles our payments processing.")

    runner.invoke(app, ["ingest", str(docs_dir), "--path", "workspace_a"])
    result = runner.invoke(app, ["search", "payments", "--path", "workspace_b"])
    assert result.exit_code == 0
    assert "No results" in result.output


def test_mcp_and_serve_use_the_ingested_workspace(tmp_path, monkeypatch):
    # Regression: both commands used to start an empty in-memory engine,
    # so an agent connected over MCP/REST could never see ingested docs.
    from typer.testing import CliRunner

    import contextflow.mcp.server as mcp_server
    from contextflow.cli.main import app

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "refunds.md").write_text("Refunds are processed within five business days.")
    workspace = str(tmp_path / ".contextflow")
    runner = CliRunner()
    assert runner.invoke(app, ["ingest", str(docs), "--path", workspace]).exit_code == 0

    captured = {}
    monkeypatch.setattr(mcp_server, "main", lambda **kw: captured.update(mcp=kw["engine"]))
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda app_, **kw: captured.update(api=app_))
    assert runner.invoke(app, ["mcp", "--path", workspace]).exit_code == 0
    assert runner.invoke(app, ["serve", "--path", workspace]).exit_code == 0

    for engine in (captured["mcp"], captured["api"].state.engine):
        hits = engine.retrieve("how long do refunds take", limit=1)
        assert hits and "five business days" in hits[0].content

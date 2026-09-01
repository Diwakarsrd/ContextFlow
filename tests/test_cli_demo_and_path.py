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

from pathlib import Path

from contextflow.connectors.filesystem.connector import FilesystemConnector


def test_filesystem_connector_sync(tmp_path: Path):
    (tmp_path / "a.md").write_text("hello from a")
    (tmp_path / "b.txt").write_text("hello from b")
    (tmp_path / "ignore.bin").write_bytes(b"\x00\x01")

    connector = FilesystemConnector(config={"path": str(tmp_path)})
    objects = list(connector.sync())

    contents = {obj.content for obj in objects}
    assert "hello from a" in contents
    assert "hello from b" in contents
    assert len(objects) == 2  # .bin excluded by default extensions

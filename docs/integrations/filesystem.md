# Filesystem Connector

Syncs text files from a local directory. Fully implemented in v0.1 — see
`src/contextflow/connectors/filesystem/connector.py`.

```python
from contextflow.connectors.filesystem.connector import FilesystemConnector

connector = FilesystemConnector(config={"path": "./docs"})
```

Config:

- `path` (required): directory to scan
- `extensions` (optional): file extensions to include, defaults to
  common text/code types

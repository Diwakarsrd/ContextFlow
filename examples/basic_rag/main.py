"""Minimal end-to-end example: ingest a folder, retrieve, print a
Context Pack. Run: python main.py ./sample_docs "your question"
"""

from __future__ import annotations

import sys

from contextflow import ContextEngine
from contextflow.connectors.filesystem.connector import FilesystemConnector


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python main.py <docs_dir> <question>")
        raise SystemExit(1)

    docs_dir, question = sys.argv[1], sys.argv[2]

    engine = ContextEngine()
    engine.sync(FilesystemConnector(config={"path": docs_dir}))

    pack = engine.context_pack(task=question, max_tokens=1000)
    print(pack.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

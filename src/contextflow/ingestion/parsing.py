"""Raw-record parsing helpers (e.g. stripping HTML/Markdown noise before
chunking). Extend per-source as connectors need it."""

from __future__ import annotations

import re


def strip_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)  # strip HTML tags
    text = re.sub(r"\s+", " ", text).strip()
    return text

"""Normalizes whitespace/encoding before content is embedded or indexed."""

from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split())

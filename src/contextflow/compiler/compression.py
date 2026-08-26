"""Content compression strategies used when a ContextObject's content is
too large to fit the remaining token budget whole.

v0.1 ships simple truncation. Extractive/abstractive summarization is a
good v0.2 contribution — see CONTRIBUTING.md.
"""

from __future__ import annotations

_CHARS_PER_TOKEN = 4


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"

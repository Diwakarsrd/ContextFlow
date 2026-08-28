"""Faithfulness: does the compiled ContextPack support the claims an
agent makes from it? v0.1 ships the interface; an LLM-judge implementation
is a good contribution — see CONTRIBUTING.md."""

from __future__ import annotations

from contextflow.core.context_pack import ContextPack


def faithfulness_score(pack: ContextPack, generated_answer: str) -> float:
    raise NotImplementedError(
        "faithfulness_score needs an LLM-judge implementation — see CONTRIBUTING.md"
    )

"""Thin, stable-surface SDK on top of `contextflow`.

The `contextflow` package is the engine itself and its internals may shift
between minor versions. `contextflow_sdk` re-exports a small, deliberately
stable surface for application developers who just want to call the
engine — framework integrations (LangGraph, CrewAI, ...) build on this,
not on `contextflow` internals directly.
"""

from contextflow import ContextEngine, ContextObject, ContextPack

__all__ = ["ContextEngine", "ContextObject", "ContextPack"]

"""ContextFlow — open-source context infrastructure for AI agents."""

from contextflow.core.context import ContextObject
from contextflow.core.context_pack import ContextPack
from contextflow.embeddings.base import EmbeddingProvider, LocalHashEmbeddingProvider
from contextflow.engine import ContextEngine, local_workspace

__version__ = "0.1.0"

__all__ = [
    "ContextEngine",
    "ContextObject",
    "ContextPack",
    "EmbeddingProvider",
    "LocalHashEmbeddingProvider",
    "__version__",
    "local_workspace",
]

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

from contextflow.connectors.base import Connector
from contextflow.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class PluginRegistry:
    """ Phase 12: ContextFlow Runtime Plugin Architecture.
    Discovers and instantiates third-party Python packages safely at runtime
    using the official Python entry_points specification, allowing engineers
    to inject proprietary Connectors or Embedding models without hard-forking the core repo.
    """
    
    def __init__(self) -> None:
        self.connectors: dict[str, type[Connector]] = {}
        self.embeddings: dict[str, type[EmbeddingProvider]] = {}
        self._discover()

    def _discover(self) -> None:
        # Discover third-party connectors
        try:
            for entry_point in importlib.metadata.entry_points(group="contextflow.connectors"):
                try:
                    plugin_class = entry_point.load()
                    if issubclass(plugin_class, Connector):
                        self.connectors[entry_point.name] = plugin_class
                        logger.info(f"Loaded plugin connector: {entry_point.name}")
                except Exception as e:
                    logger.warning(f"Failed to load connector {entry_point.name}: {e}")
        except Exception:
            pass
            
        # Discover third-party embeddings
        try:
            for entry_point in importlib.metadata.entry_points(group="contextflow.embeddings"):
                try:
                    plugin_class = entry_point.load()
                    if issubclass(plugin_class, EmbeddingProvider):
                        self.embeddings[entry_point.name] = plugin_class
                        logger.info(f"Loaded plugin embedding provider: {entry_point.name}")
                except Exception as e:
                    logger.warning(f"Failed to load embedding {entry_point.name}: {e}")
        except Exception:
            pass

    def get_connector(self, name: str, **kwargs: Any) -> Connector:
        if name not in self.connectors:
            raise KeyError(f"Connector '{name}' not found in registry.")
        return self.connectors[name](**kwargs)
        
    def get_embedding_provider(self, name: str, **kwargs: Any) -> EmbeddingProvider:
        if name not in self.embeddings:
            raise KeyError(f"Embedding provider '{name}' not found in registry.")
        return self.embeddings[name](**kwargs)

_registry = PluginRegistry()

def get_registry() -> PluginRegistry:
    return _registry

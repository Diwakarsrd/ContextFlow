from collections.abc import Iterable
from typing import Any

import pytest

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject
from contextflow.plugins import PluginRegistry


class MockProprietaryConnector(Connector):
    def authenticate(self) -> None: pass
    def discover(self) -> Iterable[str]: return ["mock_data"]
    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]: return [{"text": "secure_data"}]
    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        return ContextObject(content=raw_record["text"], source="proprietary")

def test_phase12_runtime_plugin_registry(monkeypatch):
    # Mocking standard importlib metadata for isolated testing
    import importlib.metadata
    
    class MockEntryPoint:
        def __init__(self, name, target_class):
            self.name = name
            self.target_class = target_class
        def load(self): return self.target_class
            
    def mock_entry_points(group):
        if group == "contextflow.connectors":
            return [MockEntryPoint("secure_erp", MockProprietaryConnector)]
        return []
        
    monkeypatch.setattr(importlib.metadata, "entry_points", mock_entry_points)
    
    registry = PluginRegistry()
    
    # 1. Verify dynamic runtime discovery
    assert "secure_erp" in registry.connectors
    
    # 2. Verify instantiation
    connector = registry.get_connector("secure_erp")
    assert isinstance(connector, MockProprietaryConnector)
    
    # 3. Prevent runtime crashes on missing plugins
    with pytest.raises(KeyError):
        registry.get_connector("phantom_plugin")

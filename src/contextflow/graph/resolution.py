class EntityResolver:
    """Phase 3 Core: Entity Resolution and Deduplication."""
    def __init__(self):
        self.canonical_map = {
            'acme corp': 'Acme Corporation',
            'acme': 'Acme Corporation',
            'jdoe': 'John Doe',
        }
        
    def resolve(self, entity_str: str) -> str:
        lower_ent = entity_str.lower().strip()
        return self.canonical_map.get(lower_ent, entity_str)

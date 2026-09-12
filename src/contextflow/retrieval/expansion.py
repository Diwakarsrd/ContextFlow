from typing import List

class QueryExpander:
    """Phase 2 Core: Query Expansion and Synonym Mapping."""
    def __init__(self):
        self.synonyms = {
            'revenue': ['income', 'earnings', 'profit'],
            'drop': ['decrease', 'loss', 'fall'],
            'bug': ['defect', 'issue', 'ticket']
        }
        
    def expand(self, query: str) -> List[str]:
        variations = [query]
        words = query.lower().split()
        syn_variation = [self.synonyms.get(w, [w])[0] for w in words]
        syn_query = " ".join(syn_variation)
        if syn_query != query.lower():
            variations.append(syn_query)
        return variations

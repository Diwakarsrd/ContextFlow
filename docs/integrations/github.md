# GitHub Connector

Syncs issues, pull requests, and each repo's README via the GitHub REST
API. Fully implemented in v0.1 — see
`src/contextflow/connectors/github/connector.py`.

```python
from contextflow.connectors.github.connector import GitHubConnector

connector = GitHubConnector(config={
    "token": "ghp_...",          # optional for public repos; required to
                                   # avoid the 60 req/hr unauthenticated
                                   # rate limit
    "repos": ["yourorg/yourrepo"],
    "max_items_per_repo": 100,    # optional, default 100
    "include_readme": True,       # optional, default True
})

engine.sync(connector)
```

Config:

- `token` (optional): GitHub personal access token, or set `$GITHUB_TOKEN`
- `repos` (required): list of `"owner/repo"` strings
- `include_readme` (optional): also sync each repo's README, default `True`
- `max_items_per_repo` (optional): cap on issues+PRs fetched, default `100`

Tested against a mocked GitHub API — see `tests/test_github_connector.py`.

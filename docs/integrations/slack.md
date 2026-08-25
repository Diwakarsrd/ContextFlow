# Slack Connector

Syncs channel messages and (optionally) thread replies via the Slack Web
API. Real implementation — see
`src/contextflow/connectors/slack/connector.py`.

```python
from contextflow.connectors.slack.connector import SlackConnector

connector = SlackConnector(config={
    "token": "xoxb-...",              # or $SLACK_BOT_TOKEN
    "channels": ["C0123456789"],       # channel IDs
    "channel_names": ["eng-payments"], # or resolve by name instead/also
    "include_threads": True,           # default True
    "max_messages_per_channel": 200,   # default 200
})

engine.sync(connector)
```

Needs a Slack bot token with `channels:history` + `channels:read`
(add `groups:history`/`groups:read` for private channels).

## Testing status

Tested against a **mocked** Slack Web API
(`tests/test_slack_connector.py`), including pagination, channel-name
resolution, and thread handling — including a full
`engine.sync()` → `engine.retrieve()` round trip, not just
`fetch()`/`normalize()` in isolation.

**Not tested against a real Slack workspace.** `slack.com` isn't
reachable from this project's development environment, so real-world
behavior (actual rate limits, real mrkdwn formatting edge cases, real
thread structures, pagination at scale) hasn't been verified. If you run
this against production Slack data, treat it the way you would any
integration you haven't personally run before — and consider
contributing back what you find (see CONTRIBUTING.md).

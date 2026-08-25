# Integrations

Built-in connectors (v0.1): [GitHub](github.md) and [PostgreSQL](postgres.md)
are live-tested against real infrastructure; [filesystem](filesystem.md)
is fully local and trivially real; [Slack](slack.md) and [Notion](notion.md)
are real code tested against mocked APIs only — not yet verified against
a live workspace.

Wanted (community-contributed, see root `CONTRIBUTING.md`): Slack,
Discord, Linear, Jira, Notion, Confluence, GitLab, Google Drive,
OneDrive, S3, BigQuery, Snowflake, Databricks.

Each connector should get its own page here once implemented, following
the pattern in `connectors/filesystem.md`.

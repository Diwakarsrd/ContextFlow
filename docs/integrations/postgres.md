# PostgreSQL Connector

Syncs rows from configured tables as structured context records.
Fully implemented in v0.1 — see
`src/contextflow/connectors/postgres/connector.py`. Requires the
`postgres` extra: `pip install "contextflow[postgres]"`.

```python
from contextflow.connectors.postgres.connector import PostgresConnector

connector = PostgresConnector(config={
    "dsn": "postgresql://user:pass@host/db",
    "tables": [
        {"table": "customers", "text_columns": ["name", "notes"], "limit": 1000},
        "public.orders",   # plain string form: syncs all columns
    ],
})

engine.sync(connector)
```

Table and column identifiers are validated against a strict allow-list
(alphanumeric, underscore, dot) before being interpolated into SQL, since
they can't be passed as bound parameters — see `_validate_identifier` in
the connector source.

Logic is unit-tested (`tests/test_postgres_connector.py`) and the full
connect → fetch → sync → retrieve path is proven against a real,
running PostgreSQL instance in `tests/test_postgres_live.py` — including
a live proof that the SQL-injection guard rejects a malicious table
identifier even with a real database behind it. CI runs these against a
Postgres service container on every PR. See CONTRIBUTING.md for how to
run them locally.

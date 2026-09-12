# ruff: noqa
"""Live integration tests for PostgresConnector against a real
PostgreSQL instance.

These are separate from `tests/test_postgres_connector.py` (which tests
connector logic with no live database). These actually connect, create
tables, and query — proving the connector works end-to-end rather than
just that its identifier-validation and normalization logic is correct.

Configure via $CONTEXTOS_TEST_POSTGRES_DSN, e.g.:

    export CONTEXTOS_TEST_POSTGRES_DSN=postgresql://contextflow:contextflow@127.0.0.1:5432/contextflow_test

Tests are skipped (not failed) if no live database is reachable, so CI/
contributors without a local Postgres aren't blocked.
"""

from __future__ import annotations

import os

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg not installed (pip install 'contextflow[postgres]')")

from contextflow.connectors.postgres.connector import PostgresConnector
from contextflow.engine import ContextEngine

DSN = os.environ.get(
    "CONTEXTOS_TEST_POSTGRES_DSN",
    "postgresql://contextflow:contextflow@127.0.0.1:5432/contextflow_test",
)


def _live_db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2):
            return True
    except psycopg.Error:
        return False


pytestmark = pytest.mark.skipif(
    not _live_db_available(),
    reason=f"No live PostgreSQL reachable at {DSN} — set $CONTEXTOS_TEST_POSTGRES_DSN or skip.",
)


@pytest.fixture
def pg_conn():
    conn = psycopg.connect(DSN, autocommit=True)
    yield conn
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS test_customers")
        cur.execute("DROP TABLE IF EXISTS test_tickets")
    conn.close()


def _seed(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE test_customers (id SERIAL PRIMARY KEY, name TEXT, notes TEXT)"
        )
        cur.execute(
            "INSERT INTO test_customers (name, notes) VALUES (%s, %s), (%s, %s)",
            ("Acme Corp", "Uses Stripe, migration planned Q4", "Widgets Inc", "Annual renewal"),
        )
        cur.execute("CREATE TABLE test_tickets (id SERIAL PRIMARY KEY, subject TEXT, body TEXT)")
        cur.execute(
            "INSERT INTO test_tickets (subject, body) VALUES (%s, %s)",
            ("Refund request", "Customer wants a refund within the 30 day window"),
        )


def test_connector_authenticates_against_live_db(pg_conn):
    connector = PostgresConnector(config={"dsn": DSN, "tables": ["test_customers"]})
    connector.authenticate()  # should not raise


def test_connector_fetches_real_rows(pg_conn):
    _seed(pg_conn)
    connector = PostgresConnector(
        config={
            "dsn": DSN,
            "tables": [{"table": "test_customers", "text_columns": ["name", "notes"]}],
        }
    )
    connector.authenticate()
    rows = list(connector.fetch("test_customers"))
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"Acme Corp", "Widgets Inc"}


def test_connector_respects_limit(pg_conn):
    _seed(pg_conn)
    connector = PostgresConnector(
        config={"dsn": DSN, "tables": [{"table": "test_customers", "limit": 1}]}
    )
    connector.authenticate()
    rows = list(connector.fetch("test_customers"))
    assert len(rows) == 1


def test_full_sync_and_retrieve_against_live_db(pg_conn):
    _seed(pg_conn)
    connector = PostgresConnector(
        config={
            "dsn": DSN,
            "tables": [
                {"table": "test_customers", "text_columns": ["name", "notes"]},
                {"table": "test_tickets", "text_columns": ["subject", "body"]},
            ],
        }
    )
    engine = ContextEngine()
    count = engine.sync(connector)
    assert count == 3

    results = engine.retrieve("refund")
    assert any("refund" in obj.content.lower() for obj in results)


def test_rejects_unsafe_table_identifier_even_with_live_db(pg_conn):
    connector = PostgresConnector(
        config={"dsn": DSN, "tables": ["customers; DROP TABLE test_customers;--"]}
    )
    with pytest.raises(ValueError):
        list(connector.discover())

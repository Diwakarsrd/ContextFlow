import pytest

from contextflow.connectors.postgres.connector import PostgresConnector, _validate_identifier


def test_validate_identifier_accepts_safe_names():
    assert _validate_identifier("public.customers") == "public.customers"
    assert _validate_identifier("orders") == "orders"


def test_validate_identifier_rejects_injection_attempts():
    with pytest.raises(ValueError):
        _validate_identifier("customers; DROP TABLE users;--")
    with pytest.raises(ValueError):
        _validate_identifier("customers WHERE 1=1")


def test_discover_validates_and_normalizes_table_names():
    connector = PostgresConnector(
        config={"dsn": "postgresql://x", "tables": ["customers", {"table": "orders"}]}
    )
    assert list(connector.discover()) == ["customers", "orders"]


def test_normalize_builds_content_and_metadata():
    connector = PostgresConnector(config={"dsn": "postgresql://x", "tables": ["customers"]})
    raw = {"__table__": "customers", "id": 1, "name": "Acme", "plan": "enterprise"}
    obj = connector.normalize(raw)
    assert obj.type == "record"
    assert "Acme" in obj.content
    assert obj.metadata["table"] == "customers"

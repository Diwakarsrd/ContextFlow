"""PostgreSQL connector: syncs rows from configured tables as structured
context records.

Config:
    dsn: PostgreSQL connection string, e.g. "postgresql://user:pass@host/db"
    tables: list of entries, each either a string ("public.customers") or
            a dict {"table": str, "text_columns": [str, ...], "limit": int}.
            `text_columns` controls which columns are concatenated into
            ContextObject.content; if omitted, all columns are used.

Requires the `postgres` extra: pip install "contextflow[postgres]"
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from contextflow.connectors.base import Connector
from contextflow.core.context import ContextObject

_IDENTIFIER_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")


def _validate_identifier(name: str) -> str:
    """Guard against SQL injection via table/column names, which can't be
    parameterized in DDL/identifier position."""
    if not name or not set(name) <= _IDENTIFIER_ALLOWED:
        raise ValueError(f"Unsafe table/column identifier: {name!r}")
    return name


class PostgresConnector(Connector):
    name = "postgres"

    def authenticate(self) -> None:
        dsn = self.config.get("dsn")
        if not dsn:
            raise RuntimeError("PostgresConnector requires config['dsn']")
        try:
            import psycopg
        except ImportError as exc:
            raise ImportError(
                'PostgresConnector requires the "postgres" extra: '
                'pip install "contextflow[postgres]"'
            ) from exc
        self._conn = psycopg.connect(dsn)

    def discover(self) -> Iterable[str]:
        tables = self.config.get("tables", [])
        if not tables:
            raise RuntimeError("PostgresConnector requires config['tables']")
        names = []
        for entry in tables:
            name = entry["table"] if isinstance(entry, dict) else entry
            names.append(_validate_identifier(name))
        return names

    def _table_config(self, table: str) -> dict[str, Any]:
        for entry in self.config.get("tables", []):
            if isinstance(entry, dict) and entry["table"] == table:
                return entry
            if entry == table:
                return {"table": table}
        return {"table": table}

    def fetch(self, resource_id: str) -> Iterable[dict[str, Any]]:
        table_cfg = self._table_config(resource_id)
        limit = table_cfg.get("limit", 1000)
        text_columns = table_cfg.get("text_columns")
        columns_sql = (
            ", ".join(_validate_identifier(c) for c in text_columns) if text_columns else "*"
        )

        with self._conn.cursor() as cur:
            # Table/column names are validated above; only `limit` is a
            # runtime value and it's passed as a bound parameter.
            cur.execute(f"SELECT {columns_sql} FROM {resource_id} LIMIT %s", (limit,))
            columns = [desc.name for desc in cur.description or []]
            for row in cur.fetchall():
                yield dict(zip(columns, row)) | {"__table__": resource_id}

    def normalize(self, raw_record: dict[str, Any]) -> ContextObject:
        table = raw_record.pop("__table__")
        content = " ".join(str(v) for v in raw_record.values() if v is not None)
        return ContextObject(
            type="record",
            content=content or str(raw_record),
            source=self.name,
            metadata={"table": table, **{k: str(v) for k, v in raw_record.items()}},
        )

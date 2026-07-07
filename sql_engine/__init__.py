"""
SQL Engine — DuckDB-powered core for all data operations.

Every chart render, filter, aggregation, join, and calculation is
executed as a SQL query against DuckDB, not pandas. This mirrors
how Tableau & PowerBI work: translate user intent → SQL → result.
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb


class SqlEngine:
    """Singleton DuckDB connection manager.

    - One connection per process (thread-safe via lock)
    - Can operate in-memory (:memory:) or backed by a .db file
    - Can ATTACH to PostgreSQL, MySQL, SQLite for direct SQL querying
    """

    _instance: SqlEngine | None = None
    _lock = threading.Lock()

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._conn = duckdb.connect(db_path or ":memory:")
        self._conn.execute("SET enable_progress_bar = false")
        self._mutex = threading.Lock()

        # Load standard extensions
        try:
            self._conn.execute("INSTALL 'spatial'; LOAD 'spatial'")
        except Exception:
            pass  # spatial not critical
        try:
            self._conn.execute("INSTALL 'httpfs'; LOAD 'httpfs'")
        except Exception:
            pass

        # Track attached databases so we can detach later
        self._attached: set[str] = set()

    # ── Singleton factory ──────────────────────────────────────────

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> SqlEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    # ── Connection management ──────────────────────────────────────

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        return self._conn

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ── Query execution ────────────────────────────────────────────

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute arbitrary SQL and return results as a list of dicts."""
        with self._mutex:
            try:
                if params:
                    result = self._conn.execute(sql, params)
                else:
                    result = self._conn.execute(sql)
                if result.description:
                    cols = [desc[0] for desc in result.description]
                    rows = result.fetchall()
                    return [dict(zip(cols, row)) for row in rows]
                return []
            except Exception as exc:
                raise RuntimeError(f"DuckDB query failed:\n{sql}\nError: {exc}") from exc

    def query_df(self, sql: str) -> Any:
        """Execute SQL and return a pandas DataFrame (for Plotly input)."""
        with self._mutex:
            return self._conn.execute(sql).fetchdf()

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        """Execute a DDL / DML statement (no result rows)."""
        with self._mutex:
            if params:
                self._conn.execute(sql, params)
            else:
                self._conn.execute(sql)

    # ── Table / view management ────────────────────────────────────

    def table_exists(self, name: str) -> bool:
        rows = self.query(
            "SELECT count(*) AS cnt FROM information_schema.tables "
            "WHERE table_name = ? AND table_schema = 'main'",
            [name],
        )
        return rows[0]["cnt"] > 0 if rows else False

    def drop_table(self, name: str) -> None:
        self.execute(f"DROP TABLE IF EXISTS {_qi(name)}")

    def drop_view(self, name: str) -> None:
        self.execute(f"DROP VIEW IF EXISTS {_qi(name)}")

    def list_tables(self) -> list[str]:
        rows = self.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    def list_views(self) -> list[str]:
        rows = self.query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_type = 'VIEW' "
            "ORDER BY table_name"
        )
        return [r["table_name"] for r in rows]

    # ── Ingestion ──────────────────────────────────────────────────

    def ingest_csv(
        self, path: str | Path, table_name: str, **kwargs: Any
    ) -> int:
        """Load a CSV file into a DuckDB table. Returns row count."""
        path_str = str(path).replace("\\", "/")
        header = "true" if kwargs.get("header", True) else "false"
        delim = kwargs.get("delim", ",")
        sql = (
            f"CREATE OR REPLACE TABLE {_qi(table_name)} AS "
            f"SELECT * FROM read_csv_auto('{path_str}', header={header}, delim='{delim}')"
        )
        self.execute(sql)
        return self.query(f"SELECT count(*) AS cnt FROM {_qi(table_name)}")[0]["cnt"]

    def ingest_parquet(
        self, path: str | Path, table_name: str
    ) -> int:
        """Load a Parquet file into a DuckDB table."""
        path_str = str(path).replace("\\", "/")
        self.execute(
            f"CREATE OR REPLACE TABLE {_qi(table_name)} AS "
            f"SELECT * FROM read_parquet('{path_str}')"
        )
        return self.query(f"SELECT count(*) AS cnt FROM {_qi(table_name)}")[0]["cnt"]

    def ingest_json(
        self, path: str | Path, table_name: str
    ) -> int:
        """Load a newline-delimited JSON file into a DuckDB table."""
        path_str = str(path).replace("\\", "/")
        self.execute(
            f"CREATE OR REPLACE TABLE {_qi(table_name)} AS "
            f"SELECT * FROM read_json_auto('{path_str}')"
        )
        return self.query(f"SELECT count(*) AS cnt FROM {_qi(table_name)}")[0]["cnt"]

    def ingest_rows(
        self, table_name: str, columns: list[str], rows: list[list[Any]]
    ) -> int:
        """Insert rows into a table (used for programmatic ingestion)."""
        if not rows:
            return 0
        col_list = ", ".join(_qi(c) for c in columns)
        placeholders = ", ".join(["?" for _ in columns])
        values_sql = ", ".join(
            [f"({placeholders})" for _ in rows]
        )
        flat_params = [item for row in rows for item in row]
        self.execute(
            f"INSERT INTO {_qi(table_name)} ({col_list}) VALUES {values_sql}",
            params=flat_params,
        )
        return len(rows)

    # ── Metadata ───────────────────────────────────────────────────

    def get_columns(self, table: str) -> list[dict[str, Any]]:
        """Return column metadata for a table or view."""
        rows = self.query(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = ? AND table_schema = 'main' "
            "ORDER BY ordinal_position",
            [table],
        )
        result = []
        for r in rows:
            # Get null count and uniqueness via SQL
            try:
                info = self.query(
                    f"SELECT count(*) AS total, "
                    f"count({_qi(r['column_name'])}) AS non_null, "
                    f"count(DISTINCT {_qi(r['column_name'])}) AS distinct_count "
                    f"FROM {_qi(table)}"
                )[0]
                null_count = info["total"] - info["non_null"]
            except Exception:
                null_count = 0
                info = {"distinct_count": 0}

            result.append({
                "name": r["column_name"],
                "dtype": r["data_type"],
                "nullable": r["is_nullable"] == "YES",
                "null_count": null_count,
                "unique_count": info["distinct_count"],
            })
        return result

    def table_info(self, table: str) -> dict[str, Any]:
        """Quick summary of a table."""
        cols = self.get_columns(table)
        row_count = self.query(f"SELECT count(*) AS cnt FROM {_qi(table)}")[0]["cnt"]
        return {
            "name": table,
            "row_count": row_count,
            "column_count": len(cols),
            "columns": cols,
        }

    # ── Database connectivity ──────────────────────────────────────

    def attach_postgres(
        self, alias: str, host: str, port: int, database: str,
        user: str, password: str,
    ) -> None:
        """ATTACH a PostgreSQL database for cross-database SQL queries."""
        conn_str = (
            f"host={host} port={port} dbname={database} "
            f"user={user} password={password}"
        )
        self.execute(f"ATTACH '{conn_str}' AS {_qi(alias)} (TYPE postgres)")
        self._attached.add(alias)

    def attach_mysql(
        self, alias: str, host: str, port: int, database: str,
        user: str, password: str,
    ) -> None:
        """ATTACH a MySQL database."""
        conn_str = (
            f"host={host} port={port} database={database} "
            f"user={user} password={password}"
        )
        self.execute(f"ATTACH '{conn_str}' AS {_qi(alias)} (TYPE mysql)")
        self._attached.add(alias)

    def attach_sqlite(self, alias: str, file_path: str) -> None:
        """ATTACH a SQLite database file."""
        self.execute(f"ATTACH '{file_path}' AS {_qi(alias)} (TYPE sqlite)")
        self._attached.add(alias)

    def detach(self, alias: str) -> None:
        self.execute(f"DETACH {_qi(alias)}")
        self._attached.discard(alias)


# ── Helpers ────────────────────────────────────────────────────────

def _qi(name: str) -> str:
    """Quote an identifier for safe SQL usage."""
    return f'"{name}"'


def random_table_name(prefix: str = "ds") -> str:
    """Generate a unique random table name."""
    return f"{prefix}_{uuid4().hex[:12]}"

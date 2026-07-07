"""SQL database data sources: PostgreSQL, MySQL, SQLite, Generic — all via DuckDB ATTACH.

Instead of loading data into pandas DataFrames, we use DuckDB's ATTACH
command to connect directly to external databases and query them in-place.
This way SQL queries are pushed down to the source database.
"""
from __future__ import annotations

from typing import Any, Optional

from data_sources.base import DataSource, Dataset
from sql_engine import SqlEngine, random_table_name


class SQLDatabaseSource(DataSource):
    """Base class for SQL-based data sources — uses DuckDB ATTACH."""

    source_type = "sql"
    display_name = "SQL Database"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._alias: str = ""
        self._connected = False

    def _pg_conn_str(self) -> str:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        db = self.config.get("database") or self.config.get("db") or self.config.get("dbname", "")
        user = self.config.get("user") or self.config.get("username", "")
        password = self.config.get("password", "")
        return f"host={host} port={port} dbname={db} user={user} password={password}"

    def _mysql_conn_str(self) -> str:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        db = self.config.get("database") or self.config.get("db") or self.config.get("dbname", "")
        user = self.config.get("user") or self.config.get("username", "")
        password = self.config.get("password", "")
        return f"host={host} port={port} database={db} user={user} password={password}"

    def connect(self) -> bool:
        return True  # Connection happens lazily via ATTACH in load()

    def _ensure_attached(self) -> str:
        """Ensure the external DB is attached and return the alias."""
        if hasattr(self, '_alias') and self._alias:
            return self._alias
        self._alias = f"ext_{random_table_name()}"
        # Subclasses override _attach_impl
        self._attach_impl()
        self._connected = True
        return self._alias

    def _attach_impl(self) -> None:
        """Override in subclasses with the specific ATTACH command."""
        raise NotImplementedError

    def load(self) -> list[Dataset]:
        alias = self._ensure_attached()
        engine = SqlEngine.get_instance()

        # List all tables in the attached database
        schema_name = self._get_schema_name()
        tables = engine.query(
            f"SELECT table_name FROM {_qi(alias)}.information_schema.tables "
            f"WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE'"
        )

        if not tables:
            # Try without schema qualifier
            tables = engine.query(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_catalog = '{alias}' AND table_type = 'BASE TABLE'"
            )

        datasets = []
        for t in tables:
            table_name = t["table_name"]
            # Create a DuckDB view referencing the external table
            view_name = f"_ext_{random_table_name()}"
            engine.execute(
                f"CREATE OR REPLACE VIEW {_qi(view_name)} AS "
                f"SELECT * FROM {_qi(alias)}.{_qi(schema_name)}.{_qi(table_name)}"
            )

            datasets.append(Dataset(
                name=table_name,
                table_name=view_name,
                sql_engine=engine,
                source_type=self.source_type,
                description=f"Table: {table_name} via {alias}",
            ))

        return datasets

    def _get_schema_name(self) -> str:
        return "public"

    def execute_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a raw SQL query against the attached database."""
        return SqlEngine.get_instance().query(sql)

    def get_schema(self) -> dict[str, list[dict]]:
        """Get schema info for all tables."""
        alias = self._ensure_attached()
        engine = SqlEngine.get_instance()
        tables = engine.query(
            f"SELECT table_name, column_name, data_type, is_nullable "
            f"FROM {_qi(alias)}.information_schema.columns "
            f"WHERE table_schema = '{self._get_schema_name()}' "
            f"ORDER BY table_name, ordinal_position"
        )
        schema: dict[str, list[dict]] = {}
        for row in tables:
            tname = row["table_name"]
            if tname not in schema:
                schema[tname] = []
            schema[tname].append({
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
            })
        return schema

    def disconnect(self) -> None:
        if self._alias:
            try:
                SqlEngine.get_instance().detach(self._alias)
            except Exception:
                pass
            self._alias = ""
            self._connected = False


class PostgreSQLSource(SQLDatabaseSource):
    source_type = "postgresql"
    display_name = "PostgreSQL"

    def _attach_impl(self) -> None:
        conn_str = self._pg_conn_str()
        SqlEngine.get_instance().execute(
            f"ATTACH '{conn_str}' AS {_qi(self._alias)} (TYPE postgres)"
        )


class MySQLSource(SQLDatabaseSource):
    source_type = "mysql"
    display_name = "MySQL"

    def _attach_impl(self) -> None:
        conn_str = self._mysql_conn_str()
        SqlEngine.get_instance().execute(
            f"ATTACH '{conn_str}' AS {_qi(self._alias)} (TYPE mysql)"
        )


class SQLiteSource(SQLDatabaseSource):
    source_type = "sqlite"
    display_name = "SQLite"

    def _attach_impl(self) -> None:
        db_path = self.config.get("database") or self.config.get("db") or self.config.get("file_path", "")
        SqlEngine.get_instance().execute(
            f"ATTACH '{db_path}' AS {_qi(self._alias)} (TYPE sqlite)"
        )

    def _get_schema_name(self) -> str:
        return "main"


class GenericSQLSource(SQLDatabaseSource):
    """Generic DuckDB ATTACH — uses the 'sqlalchemy' scanner if available, or postgres as fallback."""
    source_type = "generic_sql"
    display_name = "Generic SQL"

    def _attach_impl(self) -> None:
        conn_string = self.config.get("connection_string", "")
        # DuckDB supports ATTACH with different type hints
        # Try to infer the type from the connection string
        if conn_string.startswith("postgresql"):
            SqlEngine.get_instance().execute(
                f"ATTACH '{conn_string}' AS {_qi(self._alias)} (TYPE postgres)"
            )
        elif conn_string.startswith("mysql"):
            SqlEngine.get_instance().execute(
                f"ATTACH '{conn_string}' AS {_qi(self._alias)} (TYPE mysql)"
            )
        elif conn_string.startswith("sqlite"):
            SqlEngine.get_instance().execute(
                f"ATTACH '{conn_string}' AS {_qi(self._alias)} (TYPE sqlite)"
            )
        else:
            raise ValueError(
                f"Cannot infer database type from connection string. "
                f"Supported: postgresql://, mysql://, sqlite://"
            )

    def _get_schema_name(self) -> str:
        # SQLAlchemy-style connections often use "public" schema
        return "public"


def _qi(name: str) -> str:
    """Quote an identifier for safe SQL usage."""
    return f'"{name}"'

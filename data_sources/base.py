"""Abstract base classes for data sources and datasets — SQL-backed via DuckDB."""
from __future__ import annotations

import hashlib
import json
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sql_engine import SqlEngine, random_table_name


@dataclass
class Dataset:
    """A single named table loaded into DuckDB.

    Unlike the previous version which held a pd.DataFrame in memory,
    this version references a DuckDB table and uses SQL for all operations.
    """

    name: str
    table_name: str                       # DuckDB table name
    sql_engine: SqlEngine | None = None  # Shared engine instance
    description: str = ""
    source_type: str = ""                 # csv, excel, postgresql, etc.
    loaded_at: datetime = field(default_factory=datetime.now)
    _row_count_cache: int | None = None
    _column_cache: list[dict] | None = None

    def __post_init__(self) -> None:
        if self.sql_engine is None:
            self.sql_engine = SqlEngine.get_instance()
        # Warm cache
        try:
            info = self.sql_engine.table_info(self.table_name)
            self._row_count_cache = info["row_count"]
            self._column_cache = info["columns"]
        except Exception:
            pass

    @property
    def row_count(self) -> int:
        if self._row_count_cache is not None:
            return self._row_count_cache
        try:
            result = self.sql_engine.query(
                f"SELECT count(*) AS cnt FROM {_qi(self.table_name)}"
            )
            self._row_count_cache = result[0]["cnt"]
            return self._row_count_cache
        except Exception:
            return 0

    @property
    def column_count(self) -> int:
        cols = self.columns_info
        return len(cols)

    @property
    def columns_info(self) -> list[dict[str, Any]]:
        if self._column_cache is not None:
            return self._column_cache
        try:
            self._column_cache = self.sql_engine.get_columns(self.table_name)
            return self._column_cache
        except Exception:
            return []

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute arbitrary SQL against this dataset's table with optional params."""
        return self.sql_engine.query(sql, params)

    def query_df(self, sql: str, params: list[Any] | None = None) -> Any:
        """Execute SQL and return a pandas DataFrame."""
        return self.sql_engine.query_df(sql, params)

    def head(self, n: int = 10) -> list[dict[str, Any]]:
        """Get first N rows as dicts."""
        return self.sql_engine.query(
            f"SELECT * FROM {_qi(self.table_name)} LIMIT {n}"
        )

    @property
    def fingerprint(self) -> str:
        """Unique hash of the dataset for caching."""
        cols = self.columns_info
        raw = json.dumps({
            "name": self.name,
            "table": self.table_name,
            "cols": [c["name"] for c in cols],
            "row_count": self.row_count,
        }, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def summary(self) -> dict[str, Any]:
        """Return a rich SQL-powered summary of the dataset."""
        cols = self.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT", "SMALLINT", "TINYINT"
        )]
        categorical_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "VARCHAR", "TEXT", "CHAR", "STRING", "ENUM"
        )]
        date_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "DATETIME"
        )]

        # Sample data
        sample = self.head(10)

        # Basic stats via SQL for numeric columns
        basic_stats = {}
        for nc in numeric_cols[:10]:
            try:
                stats = self.sql_engine.query(
                    f"SELECT "
                    f"count(*) AS count, "
                    f"count({_qi(nc)}) AS non_null, "
                    f"min({_qi(nc)}) AS min, "
                    f"max({_qi(nc)}) AS max, "
                    f"avg({_qi(nc)}) AS mean "
                    f"FROM {_qi(self.table_name)}"
                )
                if stats:
                    basic_stats[nc] = stats[0]
            except Exception:
                pass

        return {
            "name": self.name,
            "rows": self.row_count,
            "columns": self.column_count,
            "column_names": [c["name"] for c in cols],
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "missing_data": {c["name"]: c.get("null_count", 0) for c in cols},
            "basic_stats": basic_stats,
            "sample": sample,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataset metadata (not the full data)."""
        summary = self.summary()
        return {
            "id": id(self),
            "name": self.name,
            "source_type": self.source_type,
            "description": self.description,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns_info,
            "preview_rows": summary.get("sample", []),
            "summary_stats": summary.get("basic_stats", {}),
        }


# ── Data Source base class ─────────────────────────────────────────


class DataSource(ABC):
    """Abstract data source — subclass to support a new file format or database."""

    source_type: str = "abstract"
    display_name: str = "Abstract Source"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._datasets: list[Dataset] = []
        self._engine: SqlEngine | None = None

    @property
    def engine(self) -> SqlEngine:
        if self._engine is None:
            self._engine = SqlEngine.get_instance()
        return self._engine

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection / open the resource. Return True on success."""
        ...

    @abstractmethod
    def load(self) -> list[Dataset]:
        """Load all available datasets. Returns a list of Dataset objects."""
        ...

    def disconnect(self) -> None:
        """Tear down connection."""
        pass

    @property
    def datasets(self) -> list[Dataset]:
        if not self._datasets:
            self.connect()
            self._datasets = self.load()
        return self._datasets

    def get_dataset(self, name: str) -> Dataset | None:
        for ds in self._datasets:
            if ds.name == name:
                return ds
        return None


class DataSourceRegistry:
    """Registry of available data sources (singleton-style)."""

    _sources: dict[str, DataSource] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, key: str, source: DataSource) -> None:
        with cls._lock:
            cls._sources[key] = source

    @classmethod
    def get(cls, key: str) -> DataSource | None:
        with cls._lock:
            return cls._sources.get(key)

    @classmethod
    def list(cls) -> dict[str, str]:
        with cls._lock:
            return {k: v.display_name for k, v in cls._sources.items()}

    @classmethod
    def remove(cls, key: str) -> None:
        with cls._lock:
            cls._sources.pop(key, None)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._sources.clear()

    @classmethod
    def all_datasets(cls) -> dict[str, list[Dataset]]:
        with cls._lock:
            return {key: src.datasets for key, src in cls._sources.items()}


def _qi(name: str) -> str:
    """Quote an identifier for safe SQL usage."""
    return f'"{name}"'

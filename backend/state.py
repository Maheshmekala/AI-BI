"""In-memory state management — now backed by SqlEngine and DuckDB."""
from __future__ import annotations
import uuid
import threading
from typing import Any

from sql_engine import SqlEngine
from data_sources.base import Dataset, DataSource, DataSourceRegistry


class AppState:
    """Thread-safe state store for datasets, sources, and engine reference."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._datasets: dict[str, Dataset] = {}
        self._sources: dict[str, DataSource] = {}
        self._current_dataset_id: str | None = None
        self._engine: SqlEngine | None = None

    @property
    def engine(self) -> SqlEngine:
        if self._engine is None:
            self._engine = SqlEngine.get_instance()
        return self._engine

    # ── Dataset management ──

    def add_dataset(self, dataset: Dataset, source: DataSource | None = None) -> str:
        ds_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._datasets[ds_id] = dataset
            if source:
                self._sources[ds_id] = source
        return ds_id

    def get_dataset(self, ds_id: str) -> Dataset | None:
        with self._lock:
            return self._datasets.get(ds_id)

    def list_datasets(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": ds_id,
                    "name": ds.name,
                    "source_type": ds.source_type,
                    "row_count": ds.row_count,
                    "column_count": ds.column_count,
                }
                for ds_id, ds in self._datasets.items()
            ]

    def remove_dataset(self, ds_id: str) -> bool:
        with self._lock:
            if ds_id in self._datasets:
                ds = self._datasets[ds_id]
                # Drop the DuckDB table
                try:
                    self.engine.drop_table(ds.table_name)
                except Exception:
                    pass
                del self._datasets[ds_id]
                self._sources.pop(ds_id, None)
                if self._current_dataset_id == ds_id:
                    self._current_dataset_id = None
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            for ds_id in list(self._datasets.keys()):
                try:
                    self.engine.drop_table(self._datasets[ds_id].table_name)
                except Exception:
                    pass
            self._datasets.clear()
            self._sources.clear()
            self._current_dataset_id = None

    def dataset_info(self, ds_id: str) -> dict[str, Any] | None:
        """Build a DatasetInfo-like dict from a stored dataset."""
        ds = self.get_dataset(ds_id)
        if ds is None:
            return None
        summary = ds.summary()
        return {
            "id": ds_id,
            "name": ds.name,
            "source_type": ds.source_type,
            "description": ds.description,
            "row_count": ds.row_count,
            "column_count": ds.column_count,
            "columns": summary.get("column_names", []),
            "preview_rows": summary.get("sample", []),
            "summary_stats": summary.get("basic_stats", {}),
        }

    @property
    def current_dataset_id(self) -> str | None:
        return self._current_dataset_id

    @current_dataset_id.setter
    def current_dataset_id(self, value: str | None) -> None:
        with self._lock:
            self._current_dataset_id = value


# Global singleton
state = AppState()

"""Calculation Engine — manages SQL expression-based calculated fields per dataset."""
from __future__ import annotations
import json
from typing import Any

from sql_engine import SqlEngine
from sql_engine.calculated_fields import CalculatedFieldEngine, sanitize_view_name
from data_sources.base import Dataset


class BackendCalculatedFieldEngine:
    """Manages calculated fields for datasets via the backend API.

    Each calculated field creates a DuckDB view that adds computed columns
    to the base table. All subsequent chart queries reference the view.
    """

    def __init__(self, sql_engine: SqlEngine | None = None) -> None:
        self._engine = sql_engine or SqlEngine.get_instance()
        self._calc_engine = CalculatedFieldEngine(self._engine)
        # Maps: dataset_id -> {field_name: {expression, view_name}}
        self._fields: dict[str, dict[str, dict[str, Any]]] = {}

    def create_field(
        self, dataset: Dataset, name: str, expression: str
    ) -> dict[str, Any]:
        """Create a calculated field for a dataset.

        Creates a DuckDB view that includes the calculated column.
        Updates the dataset reference to point to the new view.
        """
        view_name = sanitize_view_name(name)

        # Create view with this calculated field
        self._calc_engine.create_view(
            base_table=dataset.table_name,
            view_name=view_name,
            fields={name: expression},
            replace=True,
        )

        # Store reference
        ds_id = str(id(dataset))
        if ds_id not in self._fields:
            self._fields[ds_id] = {}
        self._fields[ds_id][name] = {
            "expression": expression,
            "view_name": view_name,
            "base_table": dataset.table_name,
        }

        return {
            "name": name,
            "expression": expression,
            "view_name": view_name,
        }

    def get_fields(self, dataset: Dataset) -> list[dict[str, Any]]:
        """List all calculated fields for a dataset."""
        ds_id = str(id(dataset))
        fields = self._fields.get(ds_id, {})
        return [
            {
                "name": name,
                "expression": info["expression"],
                "view_name": info["view_name"],
            }
            for name, info in fields.items()
        ]

    def remove_field(self, dataset: Dataset, name: str) -> bool:
        """Remove a calculated field and drop its view."""
        ds_id = str(id(dataset))
        fields = self._fields.get(ds_id, {})
        if name not in fields:
            return False

        info = fields[name]
        try:
            self._calc_engine.drop_view(info["view_name"])
        except Exception:
            pass
        del fields[name]
        return True

    def validate_expression(
        self, expression: str, dataset: Dataset
    ) -> list[str]:
        """Validate a calculated field expression."""
        return self._calc_engine.validate_expression(
            expression, dataset.table_name
        )

    def preview_expression(
        self, expression: str, dataset: Dataset, limit: int = 10
    ) -> dict[str, Any]:
        """Preview the result of a calculated field expression."""
        errors = self._calc_engine.validate_expression(expression, dataset.table_name)
        if errors:
            return {"error": errors, "values": []}

        try:
            result = dataset.query(
                f"SELECT ({expression}) AS _preview "
                f"FROM {_qi(dataset.table_name)} "
                f"WHERE ({expression}) IS NOT NULL "
                f"LIMIT {limit}"
            )
            values = [r["_preview"] for r in result] if result else []
            return {"error": None, "values": values}
        except Exception as exc:
            return {"error": [str(exc)], "values": []}

    def function_catalog(self) -> dict[str, str]:
        """Return the catalog of supported functions."""
        return CalculatedFieldEngine.function_catalog()


def _qi(name: str) -> str:
    return f'"{name}"'

"""Hierarchy Detector — auto-detects hierarchical relationships between columns."""
from __future__ import annotations
from typing import Any

from sql_engine import SqlEngine
from data_sources.base import Dataset


class HierarchyDetector:
    """Detects hierarchical relationships in datasets using SQL.

    Supported hierarchies:
    - Date: Year → Quarter → Month → Day
    - Geographic: Country → Region → State → City
    - Categorical: detected via 1:N column relationships
    """

    def __init__(self, engine: SqlEngine | None = None) -> None:
        self._engine = engine or SqlEngine.get_instance()

    def detect(self, dataset: Dataset) -> list[dict[str, Any]]:
        """Detect all hierarchies in a dataset.

        Returns list of hierarchy dicts:
        [{name, type, levels: [{column, label, cardinality}]]
        """
        hierarchies = []
        cols = dataset.columns_info

        # 1. Date hierarchy detection
        date_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "DATETIME"
        )]
        for dc in date_cols[:2]:
            hierarchies.append(self._build_date_hierarchy(dataset, dc))

        # 2. Geographic hierarchy detection
        cat_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "VARCHAR", "TEXT", "CHAR", "STRING"
        )]
        geo_keywords = [
            ("country", "Country"),
            ("region", "Region"),
            ("state", "State"),
            ("province", "Province"),
            ("city", "City"),
            ("district", "District"),
        ]

        found_geo = []
        gk_names = [k.lower() for k, _ in geo_keywords]
        for c in cat_cols:
            c_lower = c.lower().replace("_", " ").replace("-", " ")
            for kw, label in geo_keywords:
                if kw in c_lower and kw not in [f.lower() for f, _ in found_geo]:
                    found_geo.append((c, label))
                    break

        if len(found_geo) >= 2:
            hierarchies.append({
                "name": "Geographic Hierarchy",
                "type": "geographic",
                "levels": [
                    {"column": col, "label": label, "cardinality": self._get_cardinality(dataset, col)}
                    for col, label in found_geo
                ],
            })

        # 3. Detect 1:N categorical hierarchies
        if len(cat_cols) >= 2:
            # Check if any cat column is a 1:N parent of another
            for i, parent in enumerate(cat_cols[:5]):
                for child in cat_cols[i + 1:6]:
                    if self._is_one_to_many(dataset, parent, child):
                        hierarchies.append({
                            "name": f"{parent} → {child}",
                            "type": "categorical",
                            "levels": [
                                {"column": parent, "label": parent.replace("_", " ").title(), "cardinality": self._get_cardinality(dataset, parent)},
                                {"column": child, "label": child.replace("_", " ").title(), "cardinality": self._get_cardinality(dataset, child)},
                            ],
                        })

        return hierarchies

    def _build_date_hierarchy(self, dataset: Dataset, col: str) -> dict[str, Any]:
        """Build a date hierarchy from a date column."""
        table = dataset.table_name
        try:
            # Get date range
            result = dataset.query(
                f"SELECT MIN({_qi(col)}) AS min_date, MAX({_qi(col)}) AS max_date "
                f"FROM {_qi(table)}"
            )
            min_date = result[0]["min_date"] if result else None
            max_date = result[0]["max_date"] if result else None

            return {
                "name": f"{col} (Date)",
                "type": "date",
                "levels": [
                    {"column": col, "label": "Year", "cardinality": self._get_date_part_cardinality(dataset, col, "year")},
                    {"column": col, "label": "Quarter", "cardinality": self._get_date_part_cardinality(dataset, col, "quarter")},
                    {"column": col, "label": "Month", "cardinality": self._get_date_part_cardinality(dataset, col, "month")},
                    {"column": col, "label": "Day", "cardinality": self._get_date_part_cardinality(dataset, col, "day")},
                ],
                "min_date": str(min_date) if min_date else None,
                "max_date": str(max_date) if max_date else None,
            }
        except Exception:
            return {
                "name": f"{col} (Date)",
                "type": "date",
                "levels": [
                    {"column": col, "label": "Year", "cardinality": 0},
                    {"column": col, "label": "Quarter", "cardinality": 0},
                    {"column": col, "label": "Month", "cardinality": 0},
                    {"column": col, "label": "Day", "cardinality": 0},
                ],
            }

    def _get_cardinality(self, dataset: Dataset, col: str) -> int:
        try:
            result = dataset.query(
                f"SELECT count(DISTINCT {_qi(col)}) AS cnt "
                f"FROM {_qi(dataset.table_name)}"
            )
            return result[0]["cnt"] if result else 0
        except Exception:
            return 0

    def _get_date_part_cardinality(self, dataset: Dataset, col: str, part: str) -> int:
        try:
            result = dataset.query(
                f"SELECT count(DISTINCT DATE_TRUNC('{part}', {_qi(col)})) AS cnt "
                f"FROM {_qi(dataset.table_name)}"
            )
            return result[0]["cnt"] if result else 0
        except Exception:
            return 0

    def _is_one_to_many(self, dataset: Dataset, parent: str, child: str) -> bool:
        """Check if parent has a 1:N relationship with child."""
        table = dataset.table_name
        try:
            result = dataset.query(
                f"SELECT count(*) AS cnt FROM ("
                f"  SELECT {_qi(parent)}, count(DISTINCT {_qi(child)}) AS n "
                f"  FROM {_qi(table)} "
                f"  GROUP BY {_qi(parent)} "
                f"  HAVING n > 1"
                f") WHERE cnt > 0"
            )
            return result[0]["cnt"] > 0 if result else False
        except Exception:
            return False


def _qi(name: str) -> str:
    return f'"{name}"'

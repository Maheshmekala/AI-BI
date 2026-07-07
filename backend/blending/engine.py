"""Blending Engine — SQL JOIN/UNION operations to blend multiple datasets."""
from __future__ import annotations
from typing import Any

from sql_engine import SqlEngine, random_table_name
from data_sources.base import Dataset


class BlendEngine:
    """Blends multiple datasets using SQL JOINs and UNIONS.

    Mirrors Tableau's data blending — lets users combine data from
    different tables based on common columns, without needing a full ETL.
    """

    def __init__(self, engine: SqlEngine | None = None) -> None:
        self._engine = engine or SqlEngine.get_instance()

    def suggest_joins(
        self, dataset1: Dataset, dataset2: Dataset
    ) -> list[dict[str, Any]]:
        """Suggest joinable columns between two datasets.

        Uses column name similarity and data type compatibility.
        """
        cols1 = {c["name"]: c for c in dataset1.columns_info}
        cols2 = {c["name"]: c for c in dataset2.columns_info}

        suggestions = []
        for name1, info1 in cols1.items():
            for name2, info2 in cols2.items():
                # Check for exact name match
                if name1.lower() == name2.lower():
                    similarity = 1.0
                else:
                    # Token overlap similarity
                    tokens1 = set(name1.lower().replace("_", " ").replace("-", " ").split())
                    tokens2 = set(name2.lower().replace("_", " ").replace("-", " ").split())
                    if tokens1 and tokens2:
                        overlap = len(tokens1 & tokens2)
                        similarity = overlap / max(len(tokens1 | tokens2), 1)
                    else:
                        similarity = 0

                if similarity >= 0.5:
                    # Check type compatibility
                    type_compatible = self._types_compatible(info1["dtype"], info2["dtype"])
                    if type_compatible:
                        suggestions.append({
                            "left_column": name1,
                            "right_column": name2,
                            "similarity": round(similarity, 2),
                        })

        suggestions.sort(key=lambda x: x["similarity"], reverse=True)
        return suggestions[:10]

    def blend(
        self,
        datasets: list[Dataset],
        joins: list[dict[str, Any]],
        blend_type: str = "join",
        join_type: str = "left",
        output_name: str = "Blended Dataset",
    ) -> Dataset:
        """Blend multiple datasets into one.

        Args:
            datasets: List of Dataset objects to blend.
            joins: List of {left_table: str, right_table: str, left_column: str, right_column: str}
            blend_type: "join" (column-wise) or "union" (row-wise).
            join_type: "left", "inner", "outer", "cross".
            output_name: Name for the output dataset.

        Returns:
            A new Dataset backed by a DuckDB view.
        """
        if blend_type == "union":
            return self._union(datasets, output_name)
        else:
            return self._join(datasets, joins, join_type, output_name)

    def _join(
        self,
        datasets: list[Dataset],
        joins: list[dict[str, Any]],
        join_type: str,
        output_name: str,
    ) -> Dataset:
        """Perform a SQL JOIN across datasets."""
        if len(datasets) < 2:
            raise ValueError("Need at least 2 datasets to join")

        # Use the first dataset as the base
        base = datasets[0]
        view_name = f"_blend_{random_table_name(prefix='')}"

        # Build JOIN clauses
        join_clauses = []
        for i, ds in enumerate(datasets[1:], 1):
            alias = f"t{i}"
            # Find matching join config
            matching_joins = [
                j for j in joins
                if j.get("left_table") == base.table_name and j.get("right_table") == ds.table_name
            ]
            if matching_joins:
                j = matching_joins[0]
                join_clauses.append(
                    f"{join_type.upper()} JOIN {_qi(ds.table_name)} AS {alias} "
                    f"ON {_qi('t0')}.{_qi(j['left_column'])} = {alias}.{_qi(j['right_column'])}"
                )
            else:
                # Cross join if no matching columns
                join_clauses.append(f"CROSS JOIN {_qi(ds.table_name)} AS {alias}")

        from_clause = f"{_qi(base.table_name)} AS t0\n" + "\n".join(join_clauses)

        sql = f"CREATE VIEW {_qi(view_name)} AS SELECT * FROM {from_clause} LIMIT 100000"
        self._engine.execute(sql)

        return Dataset(
            name=output_name,
            table_name=view_name,
            sql_engine=self._engine,
            source_type="blend",
            description=f"Blended from {len(datasets)} datasets",
        )

    def _union(self, datasets: list[Dataset], output_name: str) -> Dataset:
        """Perform a SQL UNION ALL across datasets."""
        if len(datasets) < 2:
            raise ValueError("Need at least 2 datasets to union")

        view_name = f"_blend_{random_table_name(prefix='')}"

        union_parts = []
        for ds in datasets:
            union_parts.append(f"SELECT * FROM {_qi(ds.table_name)}")

        sql = f"CREATE VIEW {_qi(view_name)} AS " + " UNION ALL ".join(union_parts)
        self._engine.execute(sql)

        return Dataset(
            name=output_name,
            table_name=view_name,
            sql_engine=self._engine,
            source_type="blend",
            description=f"Union of {len(datasets)} datasets",
        )

    @staticmethod
    def _types_compatible(type1: str, type2: str) -> bool:
        """Check if two data types are compatible for joining."""
        numeric = {"INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"}
        strings = {"VARCHAR", "TEXT", "CHAR", "STRING"}
        dates = {"DATE", "TIMESTAMP", "DATETIME"}

        t1_upper = type1.upper()
        t2_upper = type2.upper()

        if t1_upper in numeric and t2_upper in numeric:
            return True
        if t1_upper in strings and t2_upper in strings:
            return True
        if t1_upper in dates and t2_upper in dates:
            return True
        return False


def _qi(name: str) -> str:
    return f'"{name}"'

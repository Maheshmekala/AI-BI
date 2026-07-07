"""
Shelf-to-SQL — converts drag-and-drop shelf configurations into SQL queries.

Maps the Tableau-like visual shelf model:
  - Columns shelf → GROUP BY dimensions
  - Rows shelf → aggregate measures
  - Marks card (color, size, text) → additional dimensions/measures
  - Filters shelf → WHERE clauses
"""
from __future__ import annotations

from typing import Any
from .query_builder import FilterSpec, _qi


class ShelfConfig:
    """Configuration from the drag-and-drop shelf UI."""

    def __init__(
        self,
        columns_shelf: list[str] | None = None,
        rows_shelf: list[str] | None = None,
        color: str | None = None,
        size: str | None = None,
        text: str | None = None,
        detail: list[str] | None = None,
        filters: list[FilterSpec] | None = None,
        aggregation: str = "SUM",
        chart_type: str = "bar",
    ):
        self.columns_shelf = columns_shelf or []
        self.rows_shelf = rows_shelf or []
        self.color = color
        self.size = size
        self.text = text
        self.detail = detail or []
        self.filters = filters or []
        self.aggregation = aggregation
        self.chart_type = chart_type

    @property
    def all_dimensions(self) -> list[str]:
        """All dimension fields across shelves."""
        dims = list(self.columns_shelf) + list(self.detail)
        if self.color and self.color not in dims:
            dims.append(self.color)
        return dims

    @property
    def all_measures(self) -> list[str]:
        """All measure fields."""
        measures = list(self.rows_shelf)
        if self.size and self.size not in measures:
            measures.append(self.size)
        return measures


def shelf_to_sql(config: ShelfConfig, table: str, limit: int = 5000) -> tuple[str, list[Any]]:
    """Convert a shelf configuration into a SQL query.

    Example:
        columns_shelf = ["region"]
        rows_shelf = ["sales"]
        color = "category"
        filters = [FilterSpec("year", "eq", 2024)]

    Output:
        SELECT region, SUM(sales) AS _val_sales, category AS _color
        FROM data
        WHERE year = 2024
        GROUP BY region, category
        ORDER BY _val_sales DESC
        LIMIT 5000
    """
    params: list[Any] = []
    q_table = _qi(table)
    chart_type = config.chart_type.lower()

    select_parts: list[str] = []
    group_parts: list[str] = []

    # ── Columns shelf → dimensions ──
    for col in config.columns_shelf:
        select_parts.append(f"{_qi(col)} AS _{col}")
        group_parts.append(_qi(col))

    # ── Rows shelf → measures ──
    for measure in config.rows_shelf:
        alias = f"_val_{measure}"
        select_parts.append(f"{config.aggregation}({_qi(measure)}) AS {alias}")

    # ── Color → dimension ──
    if config.color:
        select_parts.append(f"{_qi(config.color)} AS _color")
        if config.color not in config.columns_shelf:
            group_parts.append(_qi(config.color))

    # ── Size → measure ──
    if config.size:
        select_parts.append(f"{config.aggregation}({_qi(config.size)}) AS _size")

    # ── Text → dimension ──
    if config.text:
        select_parts.append(f"{_qi(config.text)} AS _text")
        if config.text not in config.columns_shelf and config.text != config.color:
            group_parts.append(_qi(config.text))

    # ── Detail → additional dimensions ──
    for col in config.detail:
        if col not in config.columns_shelf:
            select_parts.append(f"{_qi(col)} AS _{col}")
            group_parts.append(_qi(col))

    # Fallback: at least one select
    if not select_parts:
        select_parts.append("1 AS _x, count(*) AS _y")

    # ── Filters → WHERE ──
    where_parts: list[str] = []
    for f in config.filters:
        clause, f_params = _filter_to_sql(f)
        if clause:
            where_parts.append(clause)
            params.extend(f_params)

    where_sql = ""
    if where_parts:
        where_sql = "WHERE " + " AND ".join(where_parts)
        params = list(params)

    # ── Special handling per chart type ──
    if chart_type in ("box", "violin"):
        # Box plots need raw values, not aggregates
        dim_cols = ", ".join(c for c in config.columns_shelf)
        val_cols = ", ".join(config.rows_shelf)
        sql = (
            f"SELECT {dim_cols} AS _x, {val_cols} AS _y "
            f"FROM {q_table} "
            f"{where_sql} "
            f"LIMIT {limit}"
        )
        return sql, params

    elif chart_type == "pie":
        names = config.columns_shelf[0] if config.columns_shelf else "1"
        vals = config.rows_shelf[0] if config.rows_shelf else "count(*)"
        if vals == "count(*)":
            select = f"{_qi(names)} AS _names, count(*) AS _val"
        else:
            select = f"{_qi(names)} AS _names, {config.aggregation}({_qi(vals)}) AS _val"
        sql = (
            f"SELECT {select} FROM {q_table} "
            f"{where_sql} "
            f"GROUP BY _names "
            f"ORDER BY _val DESC "
            f"LIMIT {limit}"
        )
        return sql, params

    # ── Standard: GROUP BY dimensions ──
    group_sql = ""
    if group_parts:
        group_sql = "GROUP BY " + ", ".join(group_parts)

    sql = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM {q_table} "
        f"{where_sql} "
        f"{group_sql} "
        f"ORDER BY 1 DESC "
        f"LIMIT {limit}"
    )
    return sql, params


def _filter_to_sql(f: FilterSpec) -> tuple[str, list[Any]]:
    """Convert a FilterSpec to a SQL WHERE clause snippet."""
    col = _qi(f.column)
    if f.operator == "in" and f.values:
        placeholders = ", ".join(["?" for _ in f.values])
        return f"{col} IN ({placeholders})", list(f.values)
    elif f.operator == "eq" and f.value is not None:
        return f"{col} = ?", [f.value]
    elif f.operator == "neq" and f.value is not None:
        return f"{col} != ?", [f.value]
    elif f.operator in ("gt", ">") and f.value is not None:
        return f"{col} > ?", [f.value]
    elif f.operator in ("lt", "<") and f.value is not None:
        return f"{col} < ?", [f.value]
    elif f.operator == "between" and f.values and len(f.values) >= 2:
        return f"{col} BETWEEN ? AND ?", [f.values[0], f.values[1]]
    elif f.operator == "contains" and f.value is not None:
        return f"{col} LIKE ?", [f"%{f.value}%"]
    elif f.operator == "not_in" and f.values:
        placeholders = ", ".join(["?" for _ in f.values])
        return f"{col} NOT IN ({placeholders})", list(f.values)
    return "", []

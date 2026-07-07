"""
SQL Query Builder — translates user interactions into optimal SQL queries.

Every chart render, filter, aggregation, and drill-down action is
converted to a SQL query that DuckDB executes. This is the heart
of the "SQL-first" approach — no pandas DataFrames in the hot path.
"""
from __future__ import annotations

import re
from typing import Any


class FilterSpec:
    """Describes a single filter condition."""

    def __init__(
        self,
        column: str,
        operator: str = "in",
        value: Any = None,
        values: list[Any] | None = None,
    ):
        self.column = column
        self.operator = operator  # in, not_in, eq, neq, gt, gte, lt, lte, between, contains
        self.value = value
        self.values = values or ([value] if value is not None else [])


class QueryBuilder:
    """SQL query generator for charts, stats, drill-downs, and insights.

    All methods return (sql: str, params: list[Any]) tuples.
    Params are used for safe parameterized query execution.
    """

    # ── Chart queries ──────────────────────────────────────────────

    def build_chart_sql(
        self,
        table: str,
        chart_type: str = "bar",
        x_column: str | None = None,
        y_column: str | list[str] | None = None,
        aggregation: str = "none",
        color_column: str | None = None,
        filters: list[FilterSpec] | None = None,
        limit: int = 5000,
    ) -> tuple[str, list[Any]]:
        """Generate SQL for chart data.

        Handles all chart types appropriately:
        - Bar/Line/Area/Scatter → GROUP BY x, aggregate y
        - Pie → GROUP BY names (x), aggregate values (y)
        - Histogram → bucketed x column
        - Heatmap → 2D aggregation
        - Box/Violin → GROUP BY x, list y
        """
        ct = chart_type.lower()
        params: list[Any] = []
        q_table = _qi(table)

        # Resolve x and y columns
        x_col = x_column
        y_col = y_column
        if isinstance(y_col, list):
            y_col = y_col[0] if y_col else None

        # Determine the SQL components
        select_parts: list[str] = []
        group_parts: list[str] = []
        where_clauses: list[str] = []
        agg_func = self._resolve_aggregation(aggregation, ct)

        # — Handle special chart types —
        if ct in ("histogram",):
            if x_col:
                x_expr = _qi(x_col)
                min_col = _qi(f"min_{x_col}")
                max_col = _qi(f"max_{x_col}")
                minmax = (
                    f", (SELECT min({x_expr}) AS {min_col}, "
                    f"max({x_expr}) AS {max_col} "
                    f"FROM {q_table}) AS _stats"
                )
                select_parts = [
                    f"WIDTH_BUCKET({x_expr}, _stats.{min_col}, _stats.{max_col} + 0.001, 30) AS _bin",
                    f"count(*) AS _count",
                ]
            else:
                minmax = ""
                select_parts = ["1 AS _bin", "count(*) AS _count"]
            group_parts = ["_bin"]
            sql = (
                f"SELECT {select_parts[0]}, {select_parts[1]} "
                f"FROM {q_table}{minmax} "
                f"{self._build_where(filters, params)} "
                f"GROUP BY {group_parts[0]} "
                f"ORDER BY _bin "
                f"LIMIT {limit}"
            )
            return sql, params

        elif ct == "heatmap":
            x = _qi(x_col) if x_col else "1"
            y = _qi(y_col) if y_col else "1"
            sql = (
                f"SELECT {x} AS _x, {y} AS _y, count(*) AS _count "
                f"FROM {q_table} "
                f"{self._build_where(filters, params)} "
                f"GROUP BY _x, _y "
                f"ORDER BY _count DESC "
                f"LIMIT {limit}"
            )
            return sql, params

        elif ct in ("box", "violin"):
            x = _qi(x_col) if x_col else "'all'"
            y = _qi(y_col) if y_col else "1"
            sql = (
                f"SELECT {x} AS _x, {y} AS _y "
                f"FROM {q_table} "
                f"{self._build_where(filters, params)} "
                f"WHERE {y} IS NOT NULL "
                f"{'AND ' + x + ' IS NOT NULL' if x_col else ''} "
                f"LIMIT {limit}"
            )
            if x_col:
                sql += f" OFFSET 0"  # ensure valid syntax
            return sql, params

        elif ct == "pie":
            names = _qi(x_col) if x_col else "'all'"
            if y_col and agg_func != "none":
                val_expr = f"{agg_func}({_qi(y_col)}) AS _val"
            else:
                val_expr = "count(*) AS _val"
            sql = (
                f"SELECT {names} AS _names, {val_expr} "
                f"FROM {q_table} "
                f"{self._build_where(filters, params)} "
                f"GROUP BY _names "
                f"ORDER BY _val DESC "
                f"LIMIT {limit}"
            )
            return sql, params

        # — Standard chart types (bar, line, area, scatter, funnel) —
        select_cols = []
        group_cols = []

        if x_col:
            select_cols.append(f"{_qi(x_col)} AS _x")
            group_cols.append(_qi(x_col))

        if color_column:
            select_cols.append(f"{_qi(color_column)} AS _color")
            group_cols.append(_qi(color_column))

        if y_col and agg_func != "none":
            select_cols.append(f"{agg_func}({_qi(y_col)}) AS _y")
            select_cols.append(f"count(*) AS _count")
        elif y_col:
            select_cols.append(f"{_qi(y_col)} AS _y")
        else:
            select_cols.append("count(*) AS _y")

        if not select_cols:
            select_cols.append("1 AS _x, count(*) AS _y")

        order_col = "_x" if ct in ("line", "area") else "_y"
        order_dir = "ASC" if ct in ("line", "area") else "DESC"
        sql = (
            f"SELECT {', '.join(select_cols)} "
            f"FROM {q_table} "
            f"{self._build_where(filters, params)} "
            f"{'GROUP BY ' + ', '.join(group_cols) if group_cols else ''} "
            f"ORDER BY {order_col} {order_dir} "
            f"LIMIT {limit}"
        )
        return sql, params

    # ── Statistical queries ──────────────────────────────────────

    def build_stats_sql(
        self, table: str, columns: list[str] | None = None
    ) -> tuple[str, list[Any]]:
        """Generate SQL for descriptive statistics on numeric columns."""
        q_table = _qi(table)

        if columns:
            col_exprs = ", ".join(
                f"COUNT({_qi(c)}) AS count_{c}, "
                f"AVG({_qi(c)}) AS mean_{c}, "
                f"STDDEV_SAMP({_qi(c)}) AS std_{c}, "
                f"MIN({_qi(c)}) AS min_{c}, "
                f"MAX({_qi(c)}) AS max_{c}, "
                f"VAR_SAMP({_qi(c)}) AS variance_{c}"
                for c in columns
            )
        else:
            # Query information_schema for numeric columns first
            col_sql = (
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND table_schema = 'main' "
                f"AND data_type IN ('INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC', 'HUGEINT')"
            )
            # We'll just do a general query and let the backend compute
            col_exprs = "count(*) AS _row_count"

        sql = f"SELECT {col_exprs} FROM {q_table}"
        return sql, []

    def build_correlation_sql(
        self, table: str, col1: str, col2: str
    ) -> tuple[str, list[Any]]:
        """Generate SQL for Pearson correlation between two columns."""
        sql = (
            f"SELECT CORR({_qi(col1)}, {_qi(col2)}) AS correlation, "
            f"COVAR_SAMP({_qi(col1)}, {_qi(col2)}) AS covariance, "
            f"count(*) AS sample_size "
            f"FROM {_qi(table)} "
            f"WHERE {_qi(col1)} IS NOT NULL AND {_qi(col2)} IS NOT NULL"
        )
        return sql, []

    def build_trend_sql(
        self, table: str, column: str, date_column: str | None = None
    ) -> tuple[str, list[Any]]:
        """Generate SQL for trend / linear regression."""
        if date_column:
            order_expr = f"EXTRACT('epoch' FROM {_qi(date_column)})"
        else:
            order_expr = "rowid"

        sql = (
            f"SELECT {order_expr} AS _x, {_qi(column)} AS _y "
            f"FROM {_qi(table)} "
            f"WHERE {_qi(column)} IS NOT NULL "
            f"ORDER BY _x"
        )
        return sql, []

    def build_kpi_sql(
        self, table: str, columns: list[str] | None = None
    ) -> tuple[str, list[Any]]:
        """Generate SQL for KPI metrics (first/last values + changes)."""
        q_table = _qi(table)
        if not columns:
            # Get column names from info schema
            return "SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = 'main'", [table]

        kpi_parts = []
        for c in columns:
            kpi_parts.append(
                f"AVG({_qi(c)}) AS avg_{c}, "
                f"MIN({_qi(c)}) AS min_{c}, "
                f"MAX({_qi(c)}) AS max_{c}"
            )
        sql = f"SELECT {', '.join(kpi_parts)} FROM {q_table}"
        return sql, []

    def build_drill_sql(
        self,
        table: str,
        dimensions: list[str],
        measures: list[str],
        level: int = 0,
        filters: list[FilterSpec] | None = None,
        drill_values: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any]]:
        """Generate SQL for drill-down queries.

        Args:
            table: DuckDB table name
            dimensions: hierarchy dimensions (e.g. ['year', 'quarter', 'month'])
            measures: agg columns (e.g. ['sales'])
            level: current drill level (0 = top)
            filters: global filter specs
            drill_values: values from parent drill steps
        """
        params: list[Any] = []
        q_table = _qi(table)

        # Current dimension to group by
        current_dim = dimensions[min(level, len(dimensions) - 1)]
        select_cols = [f"{_qi(current_dim)} AS _dimension"]

        for m in measures:
            select_cols.append(f"SUM({_qi(m)}) AS sum_{m}")
            select_cols.append(f"COUNT({_qi(m)}) AS count_{m}")
            select_cols.append(f"AVG({_qi(m)}) AS avg_{m}")

        # Build WHERE clause from drill_values (parent filter)
        where_parts: list[str] = []
        if drill_values:
            for dim, val in drill_values.items():
                where_parts.append(f"{_qi(dim)} = ?")
                params.append(val)

        # Add global filters
        if filters:
            for f in filters:
                clause, f_params = self._filter_to_sql(f)
                if clause:
                    where_parts.append(clause)
                    params.extend(f_params)

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        sql = (
            f"SELECT {', '.join(select_cols)} "
            f"FROM {q_table} "
            f"{where_sql} "
            f"GROUP BY _dimension "
            f"ORDER BY _dimension "
            f"LIMIT 1000"
        )
        return sql, params

    # ── Filter helpers ────────────────────────────────────────────

    def _build_where(
        self, filters: list[FilterSpec] | None, params: list[Any]
    ) -> str:
        """Build WHERE clause from filter specs, appending params."""
        if not filters:
            return ""
        clauses: list[str] = []
        for f in filters:
            clause, f_params = self._filter_to_sql(f)
            if clause:
                clauses.append(clause)
                params.extend(f_params)
        return "WHERE " + " AND ".join(clauses) if clauses else ""

    def _filter_to_sql(self, f: FilterSpec) -> tuple[str, list[Any]]:
        """Convert a FilterSpec to a SQL WHERE clause snippet."""
        col = _qi(f.column)

        if f.operator == "in" and f.values:
            placeholders = ", ".join(["?" for _ in f.values])
            return f"{col} IN ({placeholders})", list(f.values)

        elif f.operator == "not_in" and f.values:
            placeholders = ", ".join(["?" for _ in f.values])
            return f"{col} NOT IN ({placeholders})", list(f.values)

        elif f.operator == "eq" and f.value is not None:
            return f"{col} = ?", [f.value]

        elif f.operator == "neq" and f.value is not None:
            return f"{col} != ?", [f.value]

        elif f.operator in ("gt", ">" ) and f.value is not None:
            return f"{col} > ?", [f.value]

        elif f.operator in ("gte", ">=") and f.value is not None:
            return f"{col} >= ?", [f.value]

        elif f.operator in ("lt", "<") and f.value is not None:
            return f"{col} < ?", [f.value]

        elif f.operator in ("lte", "<=") and f.value is not None:
            return f"{col} <= ?", [f.value]

        elif f.operator == "between" and len(f.values) >= 2:
            return f"{col} BETWEEN ? AND ?", [f.values[0], f.values[1]]

        elif f.operator == "contains" and f.value is not None:
            return f"{col} LIKE ?", [f"%{f.value}%"]

        return "", []

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_aggregation(agg: str, chart_type: str) -> str:
        """Map user-facing aggregation names to SQL functions."""
        agg_map = {
            "sum": "SUM",
            "mean": "AVG",
            "avg": "AVG",
            "count": "COUNT",
            "min": "MIN",
            "max": "MAX",
            "median": "MEDIAN",
            "std": "STDDEV_SAMP",
            "var": "VAR_SAMP",
            "none": "none",
            "": "none",
        }
        resolved = agg_map.get(agg.lower(), agg.upper())

        # For certain chart types, default aggregation
        if resolved == "none" and chart_type in ("bar", "line", "area", "scatter"):
            return "SUM"
        return resolved

    def build_table_schema_sql(self, table: str) -> str:
        """Return SQL that describes the table schema."""
        return (
            f"SELECT column_name, data_type, is_nullable "
            f"FROM information_schema.columns "
            f"WHERE table_name = '{table}' AND table_schema = 'main' "
            f"ORDER BY ordinal_position"
        )

    def build_sample_sql(self, table: str, limit: int = 100) -> str:
        return f"SELECT * FROM {_qi(table)} LIMIT {limit}"


def _qi(name: str) -> str:
    """Quote an identifier for safe SQL usage."""
    return f'"{name}"'

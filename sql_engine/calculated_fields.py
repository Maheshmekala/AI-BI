"""
Calculated Fields — user-defined SQL expressions stored as views.

Users define new columns using SQL expressions:
    profit_margin = (revenue - cost) / revenue * 100
    full_name = first_name || ' ' || last_name
    year = EXTRACT('year' FROM order_date)

These are validated and persisted as DuckDB views on top of base tables.
"""
from __future__ import annotations

import re
from typing import Any

from .query_builder import _qi

# ── Supported SQL functions for calculated fields ──────────────────

SUPPORTED_FUNCTIONS: dict[str, str] = {
    # Math
    "ABS": "ABS(x)",
    "ROUND": "ROUND(x, decimals)",
    "CEIL": "CEIL(x)",
    "FLOOR": "FLOOR(x)",
    "POWER": "POWER(x, exp)",
    "SQRT": "SQRT(x)",
    "LOG": "LOG(x)",
    "LN": "LN(x)",
    "MOD": "MOD(x, y)",
    # String
    "CONCAT": "CONCAT(str1, str2, ...)",
    "LOWER": "LOWER(str)",
    "UPPER": "UPPER(str)",
    "LENGTH": "LENGTH(str)",
    "TRIM": "TRIM(str)",
    "SUBSTR": "SUBSTR(str, start, length)",
    "REPLACE": "REPLACE(str, from, to)",
    "STRPOS": "STRPOS(str, substr)",
    # Date
    "DATE_TRUNC": "DATE_TRUNC('month', date_col)",
    "DATE_PART": "DATE_PART('year', date_col)",
    "EXTRACT": "EXTRACT('year' FROM date_col)",
    "DATEDIFF": "DATEDIFF('day', start_date, end_date)",
    "DATEADD": "DATEADD('day', 7, date_col)",
    "YEAR": "EXTRACT('year' FROM date_col)",
    "MONTH": "EXTRACT('month' FROM date_col)",
    "DAY": "EXTRACT('day' FROM date_col)",
    "QUARTER": "EXTRACT('quarter' FROM date_col)",
    "WEEK": "EXTRACT('week' FROM date_col)",
    "WEEKDAY": "EXTRACT('dow' FROM date_col) + 1",
    # Conditional
    "CASE": "CASE WHEN condition THEN result ELSE default END",
    "COALESCE": "COALESCE(column, default_value)",
    "NULLIF": "NULLIF(a, b)",
    "IFNULL": "IFNULL(column, default_value)",
    # Window / Aggregate
    "SUM": "SUM(column) OVER (PARTITION BY ...)",
    "AVG": "AVG(column) OVER (...)",
    "RANK": "RANK() OVER (ORDER BY ...)",
    "ROW_NUMBER": "ROW_NUMBER() OVER (...)",
    "LAG": "LAG(column, offset) OVER (...)",
    "LEAD": "LEAD(column, offset) OVER (...)",
    "FIRST": "FIRST(column ORDER BY ...)",
    "LAST": "LAST(column ORDER BY ...)",
    # Type
    "CAST": "CAST(column AS type)",
    "TRY_CAST": "TRY_CAST(column AS type)",
}


class CalculatedFieldError(Exception):
    """Raised when a calculated field expression is invalid."""
    pass


class CalculatedFieldEngine:
    """Manages calculated field creation, validation, and resolution."""

    # Disallowed patterns — SQL injection / dangerous operations
    DISALLOWED_PATTERNS: list[re.Pattern] = [
        re.compile(r"(DROP|ALTER|DELETE|INSERT|UPDATE|TRUNCATE)\s", re.I),
        re.compile(r"__import__", re.I),
        re.compile(r"exec\s*\(", re.I),
        re.compile(r"eval\s*\(", re.I),
        re.compile(r"ATTACH\s", re.I),
        re.compile(r"DETACH\s", re.I),
        re.compile(r"CREATE\s+(OR\s+REPLACE\s+)?TABLE", re.I),
    ]

    def __init__(self, sql_engine: Any) -> None:
        self._engine = sql_engine

    def validate_expression(
        self, expression: str, base_table: str
    ) -> list[str]:
        """Validate a calculated field expression.

        Returns a list of error messages (empty = valid).
        """
        errors: list[str] = []
        clean = expression.strip().rstrip(";")

        # 1. Check disallowed patterns
        for pattern in self.DISALLOWED_PATTERNS:
            if pattern.search(clean):
                errors.append(f"Expression contains disallowed operation: {pattern.pattern}")

        if errors:
            return errors

        # 2. Check for unbalanced parentheses
        if clean.count("(") != clean.count(")"):
            errors.append("Unbalanced parentheses")

        if errors:
            return errors

        # 3. Try to validate by running a SELECT with LIMIT 0
        try:
            test_sql = f"SELECT {clean} AS _test_val FROM {_qi(base_table)} WHERE 1=0"
            self._engine.query(test_sql)
        except Exception as exc:
            errors.append(f"Expression validation failed: {exc}")

        return errors

    def create_view(
        self,
        base_table: str,
        view_name: str,
        fields: dict[str, str],
        replace: bool = True,
    ) -> str:
        """Create a view with calculated fields on top of a base table.

        Args:
            base_table: The source table name.
            view_name: The name for the new view.
            fields: Dict of {field_name: sql_expression}.
            replace: If True, replaces existing view.

        Returns:
            The SQL CREATE VIEW statement that was executed.
        """
        if not fields:
            return base_table  # No calculations needed

        # Validate all expressions first
        for name, expr in fields.items():
            errors = self.validate_expression(expr, base_table)
            if errors:
                raise CalculatedFieldError(
                    f"Invalid expression for '{name}': {'; '.join(errors)}"
                )

        # Build the SELECT list: all base columns + calculated fields
        all_fields: list[str] = ["*"]

        for name, expr in fields.items():
            clean_expr = expr.strip().rstrip(";")
            all_fields.append(f"({clean_expr}) AS {_qi(name)}")

        select_list = ", ".join(all_fields)
        or_replace = " OR REPLACE" if replace else ""

        sql = (
            f"CREATE{or_replace} VIEW {_qi(view_name)} AS "
            f"SELECT {select_list} FROM {_qi(base_table)}"
        )

        self._engine.execute(sql)
        return view_name

    def drop_view(self, view_name: str) -> None:
        """Remove a calculated field view."""
        self._engine.execute(f"DROP VIEW IF EXISTS {_qi(view_name)}")

    def list_calculated_fields(self, base_table: str) -> list[dict[str, Any]]:
        """List active calculated field views for a table."""
        views = self._engine.list_views()
        result = []
        for v in views:
            if v.startswith("_calc_"):
                # Extract the base table reference
                try:
                    cols = self._engine.get_columns(v)
                    result.append({
                        "view_name": v,
                        "base_table": base_table,
                        "columns": cols,
                    })
                except Exception:
                    pass
        return result

    @staticmethod
    def function_catalog() -> dict[str, str]:
        """Return the catalog of supported functions for UI display."""
        return dict(SUPPORTED_FUNCTIONS)


def sanitize_view_name(name: str) -> str:
    """Convert a user-provided field name to a safe view identifier."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not safe or safe[0].isdigit():
        safe = f"calc_{safe}"
    return f"_calc_{safe}"

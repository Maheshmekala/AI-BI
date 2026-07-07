"""Auto-insights, KPI identification, and statistical analysis — SQL-powered.

All statistical computations use SQL aggregate/window functions against DuckDB.
No pandas/scipy in the hot path. Results are computed at the database level.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from data_sources.base import Dataset
from sql_engine import SqlEngine
from sql_engine.query_builder import QueryBuilder, _qi


class InsightsEngine:
    """Statistical + LLM-powered insights engine — SQL-first."""

    EXCLUDED_TREND_COLUMNS: frozenset[str] = frozenset({
        "id", "zip", "postal", "code", "latitude", "longitude",
        "lat", "lng", "lon", "record_id", "index", "row_id", "timestamp",
    })

    def __init__(self, sql_engine: SqlEngine | None = None, llm: Any | None = None) -> None:
        self._engine = sql_engine or SqlEngine.get_instance()
        self.llm = llm
        self.qb = QueryBuilder()

    def analyze(self, dataset: Dataset, llm: Any | None = None) -> dict[str, Any]:
        """Run a full analysis pipeline on a dataset using SQL."""
        if llm is not None:
            self.llm = llm
        return {
            "overview": self._overview(dataset),
            "statistical": self._statistical_analysis(dataset),
            "correlations": self._correlation_analysis(dataset),
            "outliers": self._find_outliers(dataset),
            "trends": self._detect_trends(dataset),
            "kpis": self._identify_kpis(dataset),
            "llm_insights": self._llm_insights(dataset),
        }

    def _overview(self, dataset: Dataset) -> dict:
        table = dataset.table_name
        try:
            result = dataset.query(
                f"SELECT count(*) AS rows, "
                f"count(DISTINCT 1) AS columns, "
                f"sum(CASE WHEN false THEN 1 ELSE 0 END) AS placeholder "
                f"FROM {_qi(table)}"
            )
            row_count = result[0]["rows"] if result else 0
            col_count = dataset.column_count

            # Duplicate rows
            dup_result = dataset.query(
                f"SELECT count(*) - count(DISTINCT *) AS duplicate_rows "
                f"FROM {_qi(table)}"
            )
            dups = dup_result[0]["duplicate_rows"] if dup_result else 0

            # Completeness
            cols = dataset.columns_info
            null_counts = []
            for c in cols:
                try:
                    nr = dataset.query(
                        f"SELECT count(*) AS total, "
                        f"count({_qi(c['name'])}) AS non_null "
                        f"FROM {_qi(table)}"
                    )
                    if nr:
                        null_counts.append(nr[0]["total"] - nr[0]["non_null"])
                except Exception:
                    pass

            total_cells = row_count * max(col_count, 1)
            total_nulls = sum(null_counts)
            completeness = round((1 - total_nulls / total_cells) * 100, 1) if total_cells > 0 else 100

            return {
                "name": dataset.name,
                "rows": row_count,
                "columns": col_count,
                "duplicate_rows": dups,
                "completeness": completeness,
            }
        except Exception as exc:
            return {"error": str(exc), "rows": 0, "columns": 0, "duplicate_rows": 0, "completeness": 0}

    def _statistical_analysis(self, dataset: Dataset) -> dict:
        """Compute descriptive statistics using SQL aggregates."""
        table = dataset.table_name
        cols = dataset.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
        )]

        if not numeric_cols:
            return {"message": "No numeric columns found."}

        stats = {}
        for col in numeric_cols[:15]:  # Limit to 15 columns
            try:
                sq = (
                    f"SELECT "
                    f"count(*) AS count, "
                    f"min({_qi(col)}) AS min, "
                    f"max({_qi(col)}) AS max, "
                    f"avg({_qi(col)}) AS mean, "
                    f"median({_qi(col)}) AS median, "
                    f"stddev_samp({_qi(col)}) AS std, "
                    f"var_samp({_qi(col)}) AS variance "
                    f"FROM {_qi(table)} "
                    f"WHERE {_qi(col)} IS NOT NULL"
                )
                result = dataset.query(sq)
                if result:
                    r = result[0]
                    stats[col] = {
                        "min": r["min"],
                        "max": r["max"],
                        "mean": round(float(r["mean"]), 4) if r["mean"] is not None else None,
                        "median": round(float(r["median"]), 4) if r["median"] is not None else None,
                        "std": round(float(r["std"]), 4) if r["std"] is not None else None,
                        "variance": round(float(r["variance"]), 4) if r["variance"] is not None else None,
                        "count": r["count"],
                    }

                    # Quartiles via PERCENTILE_CONT
                    q1_result = dataset.query(
                        f"SELECT percentile_cont(0.25) WITHIN GROUP (ORDER BY {_qi(col)}) AS q1 "
                        f"FROM {_qi(table)} WHERE {_qi(col)} IS NOT NULL"
                    )
                    q3_result = dataset.query(
                        f"SELECT percentile_cont(0.75) WITHIN GROUP (ORDER BY {_qi(col)}) AS q3 "
                        f"FROM {_qi(table)} WHERE {_qi(col)} IS NOT NULL"
                    )
                    if q1_result and q3_result:
                        q1 = q1_result[0]["q1"]
                        q3 = q3_result[0]["q3"]
                        if q1 is not None and q3 is not None:
                            stats[col]["q1"] = round(float(q1), 4)
                            stats[col]["q3"] = round(float(q3), 4)
                            stats[col]["iqr"] = round(float(q3) - float(q1), 4)

            except Exception:
                continue

        return stats

    def _correlation_analysis(self, dataset: Dataset) -> dict:
        """Find significant correlations using SQL CORR()."""
        table = dataset.table_name
        cols = dataset.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
        )]

        if len(numeric_cols) < 2:
            return {"message": "Need at least 2 numeric columns for correlation."}

        significant = []
        pairs = [(numeric_cols[i], numeric_cols[j])
                 for i in range(len(numeric_cols))
                 for j in range(i + 1, len(numeric_cols))]

        for col1, col2 in pairs[:30]:  # Limit pairs
            try:
                result = dataset.query(
                    f"SELECT CORR({_qi(col1)}, {_qi(col2)}) AS corr, "
                    f"count(*) AS n "
                    f"FROM {_qi(table)} "
                    f"WHERE {_qi(col1)} IS NOT NULL AND {_qi(col2)} IS NOT NULL"
                )
                if result and result[0]["corr"] is not None:
                    val = result[0]["corr"]
                    if abs(val) >= 0.3:
                        significant.append({
                            "col1": col1,
                            "col2": col2,
                            "correlation": round(val, 3),
                            "strength": "strong" if abs(val) >= 0.7 else "moderate" if abs(val) >= 0.5 else "weak",
                            "direction": "positive" if val > 0 else "negative",
                        })
            except Exception:
                continue

        significant.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return {"significant_pairs": significant[:20]}

    def _find_outliers(self, dataset: Dataset) -> dict:
        """Detect outliers using IQR method via SQL."""
        table = dataset.table_name
        cols = dataset.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
        )]

        outliers = {}
        for col in numeric_cols[:15]:
            try:
                # Get quartiles
                q_result = dataset.query(
                    f"SELECT "
                    f"percentile_cont(0.25) WITHIN GROUP (ORDER BY {_qi(col)}) AS q1, "
                    f"percentile_cont(0.75) WITHIN GROUP (ORDER BY {_qi(col)}) AS q3, "
                    f"count(*) AS n, "
                    f"avg({_qi(col)}) AS mean "
                    f"FROM {_qi(table)} WHERE {_qi(col)} IS NOT NULL"
                )
                if not q_result or q_result[0].get("q1") is None:
                    continue

                r = q_result[0]
                q1, q3 = float(r["q1"]), float(r["q3"])
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr

                # Count outliers
                outlier_result = dataset.query(
                    f"SELECT count(*) AS outlier_count "
                    f"FROM {_qi(table)} "
                    f"WHERE {_qi(col)} IS NOT NULL "
                    f"AND ({_qi(col)} < {lower} OR {_qi(col)} > {upper})"
                )
                if outlier_result:
                    n_out = outlier_result[0]["outlier_count"]
                    total = r["n"]
                    if n_out > 0 and n_out / max(total, 1) < 0.2:
                        # Get actual outlier values
                        vals_result = dataset.query(
                            f"SELECT {_qi(col)} AS val "
                            f"FROM {_qi(table)} "
                            f"WHERE {_qi(col)} IS NOT NULL "
                            f"AND ({_qi(col)} < {lower} OR {_qi(col)} > {upper}) "
                            f"LIMIT 10"
                        )
                        outlier_vals = [v["val"] for v in vals_result] if vals_result else []

                        outliers[col] = {
                            "count": int(n_out),
                            "percentage": round(float(n_out / total * 100), 1),
                            "lower_bound": round(lower, 4),
                            "upper_bound": round(upper, 4),
                            "outlier_values": outlier_vals,
                        }
            except Exception:
                continue

        return outliers

    def _detect_trends(self, dataset: Dataset) -> list[dict]:
        """Simple trend analysis using REGR_SLOPE if available, else row-based."""
        table = dataset.table_name
        cols = dataset.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
        )]

        # Filter out non-meaningful columns for trend detection
        numeric_cols = [
            c for c in numeric_cols
            if c.lower() not in self.EXCLUDED_TREND_COLUMNS
        ]

        trends = []
        for col in numeric_cols[:10]:
            try:
                # Use row-based index for trend when no date column
                result = dataset.query(
                    f"SELECT "
                    f"REGR_SLOPE({_qi(col)}, rowid) AS slope, "
                    f"REGR_R2({_qi(col)}, rowid) AS r_squared, "
                    f"REGR_INTERCEPT({_qi(col)}, rowid) AS intercept, "
                    f"count(*) AS n "
                    f"FROM {_qi(table)} "
                    f"WHERE {_qi(col)} IS NOT NULL"
                )
                if result and result[0]["slope"] is not None:
                    r = result[0]
                    slope = float(r["slope"])
                    r2 = float(r["r_squared"]) if r["r_squared"] is not None else 0
                    if abs(slope) > 0.001:
                        trends.append({
                            "column": col,
                            "trend": "upward" if slope > 0 else "downward",
                            "slope": round(slope, 4),
                            "r_squared": round(r2, 3),
                            "significant": r2 > 0.3,
                        })
            except Exception:
                continue

        return sorted(trends, key=lambda x: abs(x["slope"]), reverse=True)

    def _identify_kpis(self, dataset: Dataset) -> list[dict]:
        """Automatically identify KPIs from the dataset using SQL."""
        table = dataset.table_name
        cols = dataset.columns_info
        numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
            "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
        )]

        kpis = []

        # Row count KPI
        count_result = dataset.query(f"SELECT count(*) AS cnt FROM {_qi(table)}")
        total_rows = count_result[0]["cnt"] if count_result else 0
        kpis.append({
            "label": "Total Records",
            "value": f"{total_rows:,}",
            "delta": f"{dataset.column_count} columns",
            "direction": "neutral",
            "is_good": True,
            "icon": "📊",
            "aggregation": "count",
        })

        for col in numeric_cols[:10]:
            try:
                # Get current and previous values for trend
                result = dataset.query(
                    f"SELECT "
                    f"avg({_qi(col)}) AS mean_val, "
                    f"min({_qi(col)}) AS min_val, "
                    f"max({_qi(col)}) AS max_val "
                    f"FROM {_qi(table)} WHERE {_qi(col)} IS NOT NULL"
                )
                if not result:
                    continue
                r = result[0]
                current = float(r["max_val"]) if r["max_val"] is not None else 0
                previous = float(r["min_val"]) if r["min_val"] is not None else 0
                change = ((current - previous) / previous * 100) if previous != 0 else 0

                direction = "up" if change > 0 else "down"
                is_good = direction == "up"

                kpis.append({
                    "label": col.replace("_", " ").title(),
                    "value": f"{current:,.2f}" if abs(current) < 1e6 else f"{current:,.0f}",
                    "delta": f"{change:+.1f}%",
                    "direction": direction,
                    "is_good": is_good,
                    "icon": "📈" if is_good else "📉",
                    "column": col,
                    "aggregation": "range",
                })
            except Exception:
                continue

        return kpis

    def _llm_insights(self, dataset: Dataset) -> str:
        """Use LLM to generate narrative insights from SQL-based summary."""
        if not self.llm:
            try:
                from llm import get_llm
                self.llm = get_llm()
            except Exception:
                return "LLM not configured"

        summary = dataset.summary()
        summary_str = json.dumps(summary, indent=2, default=str)[:3000]

        prompt = (
            f"Analyze this dataset and provide 5-7 key business insights:\n\n"
            f"Dataset: {dataset.name}\n"
            f"Rows: {summary['rows']}, Columns: {summary['columns']}\n"
            f"Numeric: {summary['numeric_columns']}\n"
            f"Categorical: {summary['categorical_columns']}\n"
            f"Missing data: {summary['missing_data']}\n\n"
            f"Full summary:\n{summary_str}\n\n"
            "For each insight include: what was found, why it matters, and a recommended action."
        )

        try:
            from llm import LLMMessage, SYSTEM_PROMPTS
            messages = [
                LLMMessage(role="system", content=SYSTEM_PROMPTS.get("insight_generator",
                    "You are a data analyst providing business insights.")),
                LLMMessage(role="user", content=prompt),
            ]
            response = self.llm.chat(messages)
            return response.content
        except Exception as exc:
            return f"Could not generate LLM insights: {exc}"


def _qi(name: str) -> str:
    """Quote an identifier."""
    return f'"{name}"'

"""Renderers for Streamlit — bridges SQL-powered visualization engine with the UI.

Every chart now has a collapsible "View SQL" section showing the DuckDB query.
"""
from __future__ import annotations
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from query_engine.engine import ChartRecommendation, QueryResult
from visualization import render_chart, build_dashboard, auto_dashboard, create_kpi_card
from sql_engine.query_builder import FilterSpec, _qi


def _highlight_sql_html(sql: str) -> str:
    """Return SQL with vibrant syntax highlighting spans for dark terminal display."""
    import re
    if not isinstance(sql, str):
        try:
            sql = str(sql)
        except Exception:
            sql = "-- No SQL generated"
    sql = (sql.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;"))
    tokens = re.split(r"(\b\w+\b|'[^']*'|\"[^\"]*\"|\s+|--[^\n]*)", sql)
    parts = []
    for token in tokens:
        upper = token.upper()
        if upper in {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'AS', 'ON',
                     'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'CROSS', 'FULL',
                     'GROUP', 'BY', 'ORDER', 'ASC', 'DESC', 'HAVING', 'LIMIT', 'OFFSET',
                     'DISTINCT', 'ALL', 'UNION', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
                     'WITH', 'RECURSIVE', 'OVER', 'PARTITION', 'NULL', 'IS', 'LIKE', 'BETWEEN',
                     'TRUE', 'FALSE', 'TYPE', 'IF', 'REPLACE', 'TABLE', 'VIEW', 'DROP',
                     'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD', 'FIRST', 'LAST'}:
            parts.append(f'<span style="color:#7dd3fc;font-weight:600;">{token}</span>')
        elif upper in {'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'MEDIAN', 'CORR', 'STDDEV',
                       'VAR', 'COALESCE', 'NULLIF', 'CAST', 'DATE_TRUNC', 'EXTRACT',
                       'DATE_PART', 'DATEDIFF', 'DATEADD', 'YEAR', 'MONTH', 'DAY',
                       'QUARTER', 'WEEK', 'WEEKDAY', 'PERCENTILE_CONT', 'REGR_SLOPE',
                       'REGR_R2', 'WIDTH_BUCKET'}:
            parts.append(f'<span style="color:#22d3ee;font-weight:600;">{token}</span>')
        elif token.startswith("'") or token.startswith('"'):
            parts.append(f'<span style="color:#a3e635;">{token}</span>')
        elif re.match(r'^\d+(\.\d+)?$', token.strip()):
            parts.append(f'<span style="color:#fb923c;">{token}</span>')
        elif token.startswith('--'):
            parts.append(f'<span style="color:#6b7280;font-style:italic;">{token}</span>')
        elif token.strip():
            parts.append(token)
        else:
            parts.append(token)
    return ''.join(parts)


def display_chart_with_sql(
    fig: go.Figure,
    sql: str,
    title: str = "Chart",
) -> None:
    """Display a Plotly chart with a dark terminal-style SQL viewer in Streamlit."""
    with st.container(border=True):
        col1, col2 = st.columns([1, 4])
        with col1:
            st.caption("📊 Chart")
        with col2:
            st.caption(title)

        st.plotly_chart(fig, use_container_width=True)

        # Dark terminal-style SQL viewer
        if sql:
            st.markdown(
                f'<div style="margin-top:8px;background:#0d1117;border:1px solid #1f2937;border-radius:8px;overflow:hidden;">'
                f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:#161b22;border-bottom:1px solid #1f2937;">'
                f'<span style="color:#7dd3fc;font-size:13px;">📝</span>'
                f'<span style="color:#7dd3fc;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;">SQL Query</span>'
                f'</div>'
                f'<pre style="margin:0;padding:14px;font-family:ui-monospace,SFMono-Regular,monospace;font-size:12px;line-height:1.6;overflow-x:auto;color:#e2e8f0;background:#0d1117;"><code>{_highlight_sql_html(sql)}</code></pre>'
                f'</div>',
                unsafe_allow_html=True,
            )


def display_query_result(
    result: QueryResult,
    dataset: Any | None = None,
) -> None:
    """Display a QueryResult in Streamlit — with SQL viewer."""
    if result.error:
        st.error(f"⚠️ {result.error}")
        return

    # Show answer
    if result.answer:
        with st.container(border=True):
            st.markdown(result.answer)

    # Show SQL if present
    if result.sql_query:
        with st.expander("📝 SQL Query", expanded=False):
            st.code(result.sql_query, language="sql")

    # Show charts with SQL
    if result.charts and dataset:
        for i, chart in enumerate(result.charts):
            try:
                fig, sql = render_chart(chart, dataset)
                display_chart_with_sql(fig, sql, title=chart.title)
            except Exception as exc:
                st.caption(f"Could not render chart: {exc}")


def display_auto_dashboard(
    dataset: Any,
    title: str = "Auto Dashboard",
    max_charts: int = 8,
    filters: list[FilterSpec] | None = None,
) -> None:
    """Auto-generate and display a dashboard with SQL viewer."""
    with st.spinner("Generating dashboard via SQL..."):
        try:
            figures_data = auto_dashboard(
                dataset,
                title=title,
                max_charts=max_charts,
                filters=filters,
            )
            cols = st.columns(2)
            for i, (fig, sql) in enumerate(figures_data):
                with cols[i % 2]:
                    display_chart_with_sql(fig, sql, title=f"Chart {i + 1}")
        except Exception as exc:
            st.warning(f"Could not auto-generate dashboard: {exc}")


def display_kpi_row(kpis: list[dict], columns: int = 4) -> None:
    """Display a row of KPI cards."""
    cols = st.columns(columns)
    for i, kpi in enumerate(kpis):
        with cols[i % columns]:
            html = create_kpi_card(
                label=kpi.get("label", ""),
                value=kpi.get("value", ""),
                delta=kpi.get("delta"),
                icon=kpi.get("icon", "📊"),
            )
            st.markdown(html, unsafe_allow_html=True)


def display_data_preview(dataset: Any, max_rows: int = 100) -> None:
    """Show a data preview with column stats — SQL-powered."""
    try:
        rows = dataset.head(max_rows)
        df = pd.DataFrame(rows) if rows else pd.DataFrame()

        st.dataframe(
            df,
            use_container_width=True,
            height=min(400, 35 * min(len(df), max_rows)),
        )
    except Exception:
        st.info("Data preview not available")

    # Show SQL stats
    with st.expander("📝 Dataset Info (SQL)"):
        st.code(
            f"SELECT count(*) AS row_count,\n"
            f"       count(DISTINCT column_name) AS column_count\n"
            f"FROM information_schema.columns\n"
            f"WHERE table_name = '{dataset.table_name}'",
            language="sql",
        )


def display_chart_selector(dataset: Any) -> None:
    """Interactive chart builder UI — with all 17 chart types and SQL preview."""
    cols_info = dataset.columns_info
    all_cols = [c["name"] for c in cols_info]
    numeric_cols = [c["name"] for c in cols_info if c["dtype"].upper() in (
        "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
    )]

    with st.form("chart_builder"):
        st.markdown("### 🎨 Custom Chart Builder (SQL-powered)")

        col1, col2, col3 = st.columns(3)
        with col1:
            chart_type = st.selectbox(
                "Chart Type",
                ["bar", "line", "scatter", "pie", "area", "histogram",
                 "box", "violin", "heatmap", "sunburst", "funnel",
                 "waterfall", "treemap", "gauge", "sankey",
                 "parallel_coordinates", "candlestick"],
            )
        with col2:
            x_col = st.selectbox("X-axis", all_cols)
        with col3:
            y_col = st.selectbox("Y-axis", all_cols if chart_type != "gauge" else all_cols)

        col4, col5, col6 = st.columns(3)
        with col4:
            color_col = st.selectbox("Color (optional)", ["None"] + all_cols)
        with col5:
            agg_method = st.selectbox("Aggregation", ["sum", "avg", "count", "min", "max", "median", "none"])
        with col6:
            st.markdown("### &nbsp;")
            st.markdown("**SQL-powered** ✓")

        title = st.text_input("Chart Title", value=f"{chart_type.replace('_', ' ').title()} Chart")

        submitted = st.form_submit_button("🎨 Generate Chart", use_container_width=True)

    if submitted:
        chart = ChartRecommendation(
            chart_type=chart_type,
            title=title,
            x_column=x_col,
            y_column=y_col,
            aggregation=agg_method,
            color_column=color_col if color_col != "None" else None,
        )
        try:
            fig, sql = render_chart(chart, dataset)
            display_chart_with_sql(fig, sql, title=title)
        except Exception as exc:
            st.error(f"Could not render chart: {exc}")

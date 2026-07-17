"""Dynamic visualization engine — SQL-powered, Plotly-rendered.

Every chart renders by:
1. Generating SQL via QueryBuilder from the chart spec + filters
2. Executing SQL against DuckDB → small aggregated result set
3. Passing the result to Plotly for rendering

The generated SQL is returned alongside the figure for the SQL viewer UI.
"""
from __future__ import annotations

import base64
import io
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from query_engine.engine import ChartRecommendation
from sql_engine import SqlEngine
from sql_engine.query_builder import QueryBuilder, FilterSpec

# MCP chart bridge for open-source color themes
try:
    from mcp_charts import apply_theme_to_fig, get_color_theme
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def _apply_chart_theme(fig: go.Figure, chart_type: str = "bar") -> go.Figure:
    """Apply open-source color themes and consistent styling to charts."""
    if HAS_MCP:
        fig = apply_theme_to_fig(fig, "tableau")
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(size=12, color="#4a5568"),
        hovermode="x unified" if chart_type in ("line", "area") else "closest",
    )
    return fig


# ── SQL-Powered chart renderer ─────────────────────────────────────


def render_chart(
    chart: ChartRecommendation,
    dataset: Any,  # data_sources.base.Dataset
    filters: list[FilterSpec] | None = None,
    width: int = 600,
    height: int = 400,
) -> tuple[go.Figure, str]:
    """Render a chart recommendation against a DuckDB-backed dataset.

    Returns:
        Tuple of (Plotly Figure, SQL query that generated the data).
    """
    chart_type = chart.chart_type.lower()

    # ── Column name resolution ──────────────────────────────────────
    # Build a lookup from dataset column names (lowercased -> original)
    # so the LLM's "city" matches the real column "City".
    actual_cols = {c["name"].lower(): c["name"] for c in dataset.columns_info}

    def _resolve_col(llm_col: str) -> str | None:
        """Resolve an LLM-provided column name to the actual dataset column
        via case-insensitive matching."""
        if not llm_col:
            return None
        key = llm_col.lower().replace("_", " ").replace("-", " ").strip()
        # Exact-ish match first
        if llm_col in actual_cols.values():
            return llm_col
        if key in actual_cols:
            return actual_cols[key]
        # Try stripping common LLM artifacts
        for real_name in actual_cols.values():
            rn_lower = real_name.lower()
            if rn_lower == key or rn_lower.replace(" ", "_") == key.replace(" ", "_") or rn_lower.replace("_", " ") == key:
                return real_name
        return None

    # Sanitize all column names — strip [object Object] contamination
    def _clean_col(val: Any, default: str = "") -> str:
        if val is None:
            return default
        # y_column can be a list[str]
        if isinstance(val, list):
            return _clean_col(val[0], default) if val else default
        s = str(val).replace("[object Object]", "").replace("object Object", "").strip()
        return s or default

    raw_x = _clean_col(chart.x_column)
    raw_y = _clean_col(chart.y_column, "" if chart.chart_type == "pie" else "")
    raw_color = _clean_col(chart.color_column)

    # Resolve to actual dataset column names
    safe_x = _resolve_col(raw_x)
    safe_y = _resolve_col(raw_y)
    safe_color = _resolve_col(raw_color)

    # Check for contamination / unresolvable columns
    check_str = raw_x + raw_y + str(chart.color_column or "")
    if "[object" in check_str or "{" in check_str:
        fig = go.Figure()
        fig.add_annotation(
            text="Chart error: contaminated column names from LLM",
            showarrow=False, font=dict(color="#e53e3e", size=12),
        )
        fig.update_layout(height=height, width=width, template="plotly_white",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig, f"-- Error: contaminated column names from LLM"

    if not safe_x and not safe_y:
        # No usable columns — skip chart silently
        fig = go.Figure()
        fig.add_annotation(text="Could not determine chart columns from your question. Try rephrasing.", showarrow=False)
        fig.update_layout(height=height, width=width, template="plotly_white",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig, "-- No usable columns"

    # Build SQL using the resolved (correct-cased) column names
    qb = QueryBuilder()
    sql, params = qb.build_chart_sql(
        table=dataset.table_name,
        chart_type=chart_type,
        x_column=safe_x,
        y_column=safe_y,
        aggregation=chart.aggregation,
        color_column=safe_color,
        filters=filters or [],
        limit=5000,
    )

    # Execute SQL — this returns only the aggregated result, not the full dataset
    try:
        result = dataset.query(sql, params)
        df = pd.DataFrame(result) if result else pd.DataFrame()
    except Exception as exc:
        fig = go.Figure()
        fig.add_annotation(text=f"Query error: {exc}", showarrow=False)
        return fig, sql

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data returned", showarrow=False)
        return fig, sql

    # Map columns to Plotly inputs
    x_col = "_x" if "_x" in df.columns else (safe_x if safe_x in df.columns else None)
    y_col = "_y" if "_y" in df.columns else (safe_y if safe_y in df.columns else None)
    color_col = "_color" if "_color" in df.columns else (safe_color if safe_color and safe_color in df.columns else None)

    fig = None

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=chart.title,
                         barmode="group", height=height, width=width)

        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, color=color_col, title=chart.title,
                          height=height, width=width, markers=True)

        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=chart.title,
                             height=height, width=width)

        elif chart_type == "pie":
            names_col = "_names" if "_names" in df.columns else x_col
            val_col = "_val" if "_val" in df.columns else y_col
            fig = px.pie(df, names=names_col, values=val_col, title=chart.title,
                         height=height, width=width, hole=0.3)

        elif chart_type == "area":
            fig = px.area(df, x=x_col, y=y_col, color=color_col, title=chart.title,
                          height=height, width=width)

        elif chart_type == "histogram":
            bin_col = "_bin" if "_bin" in df.columns else x_col
            cnt_col = "_count" if "_count" in df.columns else y_col
            fig = px.bar(df, x=bin_col, y=cnt_col, title=chart.title,
                         height=height, width=width)
            fig.update_layout(xaxis_title="Bins", yaxis_title="Count")

        elif chart_type == "heatmap":
            fig = px.density_heatmap(df, x="_x" if "_x" in df.columns else x_col,
                                     y="_y" if "_y" in df.columns else y_col,
                                     z="_count" if "_count" in df.columns else None,
                                     title=chart.title, height=height, width=width)

        elif chart_type == "box":
            fig = px.box(df, x="_x" if "_x" in df.columns else x_col,
                         y="_y" if "_y" in df.columns else y_col,
                         color=color_col, title=chart.title,
                         height=height, width=width)

        elif chart_type == "violin":
            fig = px.violin(df, x="_x" if "_x" in df.columns else x_col,
                            y="_y" if "_y" in df.columns else y_col,
                            color=color_col, title=chart.title,
                            height=height, width=width, box=True)

        elif chart_type == "sunburst":
            path_col = x_col if x_col else df.columns[0]
            val_col = y_col if y_col else None
            fig = px.sunburst(df, path=[path_col], values=val_col,
                              title=chart.title, height=height, width=width)

        elif chart_type == "funnel":
            fig = px.funnel(df, x=x_col, y=y_col, title=chart.title,
                            height=height, width=width)

        elif chart_type == "gauge":
            # Gauge renders a single value — use the first row
            if y_col and y_col in df.columns and not df.empty:
                val = float(df[y_col].iloc[0]) if df[y_col].dtype.kind in 'if' else 50
            elif y_col and df.columns[0]:
                val = 50
            else:
                val = 50
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=val,
                title={"text": chart.title},
                domain={"x": [0, 1], "y": [0, 1]},
            ))
            fig.update_layout(height=height, width=width)

        elif chart_type in ("waterfall",):
            fig = go.Figure(go.Waterfall(
                x=df[x_col] if x_col and x_col in df.columns else df.index,
                y=df[y_col] if y_col and y_col in df.columns else df.iloc[:, 0],
                name=chart.title,
            ))
            fig.update_layout(title=chart.title, height=height, width=width)

        elif chart_type in ("treemap",):
            path_col = x_col if x_col else df.columns[0]
            val_col = y_col if y_col else None
            fig = px.treemap(df, path=[path_col], values=val_col,
                             title=chart.title, height=height, width=width)

        elif chart_type in ("sankey",):
            cols = df.columns[:3]
            source_vals = df[cols[0]].tolist()
            target_vals = df[cols[1]].tolist()
            labels = []
            seen = set()
            for v in source_vals + target_vals:
                if v not in seen:
                    seen.add(v)
                    labels.append(v)
            label_to_idx = {label: i for i, label in enumerate(labels)}
            fig = go.Figure(go.Sankey(
                node=dict(
                    pad=15, thickness=20,
                    label=labels,
                ),
                link=dict(
                    source=[label_to_idx[s] for s in source_vals],
                    target=[label_to_idx[t] for t in target_vals],
                    value=df[cols[2]].tolist() if len(cols) > 2 else [1] * len(df),
                ),
            ))
            fig.update_layout(title=chart.title, height=height, width=width)

        elif chart_type in ("parallel_coordinates", "parallel"):
            dims = df.select_dtypes(include="number").columns.tolist()
            if dims:
                color_dim = dims[-1]
                fig = px.parallel_coordinates(df, dimensions=dims[:-1], color=color_dim,
                                              title=chart.title, height=height, width=width)
            else:
                fig = go.Figure()
                fig.add_annotation(text="Need numeric columns for parallel coordinates", showarrow=False)

        elif chart_type in ("candlestick",):
            if df.shape[1] >= 4:
                fig = go.Figure(go.Candlestick(
                    x=df.index,
                    open=df.iloc[:, 0],
                    high=df.iloc[:, 1],
                    low=df.iloc[:, 2],
                    close=df.iloc[:, 3],
                ))
                fig.update_layout(title=chart.title, height=height, width=width)
            else:
                fig = go.Figure()
                fig.add_annotation(text="Need 4+ columns for candlestick (O, H, L, C)", showarrow=False)

        else:
            # Default: bar chart
            fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                         title=chart.title, height=height, width=width)

    except Exception as exc:
        try:
            fig = px.bar(df, title=f"{chart.title} (fallback)", height=height, width=width)
        except Exception:
            fig = go.Figure()
            fig.add_annotation(text=f"Render error: {exc}", showarrow=False)

    if fig:
        fig = _apply_chart_theme(fig, chart_type)

    return fig, sql


# ── Chart rendering without SQL return (backward-compatible) ───────


def render_chart_figure(
    chart: ChartRecommendation,
    dataset: Any,
    filters: list[FilterSpec] | None = None,
    width: int = 600,
    height: int = 400,
) -> go.Figure:
    """Render a chart and return only the Plotly figure (no SQL)."""
    fig, _ = render_chart(chart, dataset, filters, width, height)
    return fig


# ── Dashboard builder ──────────────────────────────────────────────


def build_dashboard(
    dataset: Any,
    charts: list[ChartRecommendation],
    title: str = "Dashboard",
    columns: int = 2,
    filters: list[FilterSpec] | None = None,
) -> list[tuple[go.Figure, str]]:
    """Build a dashboard grid from chart recommendations.

    Returns list of (figure, sql) tuples.
    """
    results = []
    for chart in charts:
        fig, sql = render_chart(chart, dataset, filters)
        results.append((fig, sql))
    return results


def auto_dashboard(
    dataset: Any,
    title: str = "Auto Dashboard",
    max_charts: int = 6,
    filters: list[FilterSpec] | None = None,
) -> list[tuple[go.Figure, str]]:
    """Auto-generate a dashboard by analyzing the dataset schema."""
    charts: list[ChartRecommendation] = []
    cols = dataset.columns_info

    numeric_cols = [c["name"] for c in cols if c["dtype"].upper() in (
        "INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"
    )]
    categorical_cols = [c["name"] for c in cols if c["dtype"].upper() in (
        "VARCHAR", "TEXT", "CHAR", "STRING"
    )]
    date_cols = [c["name"] for c in cols if c["dtype"].upper() in (
        "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "DATETIME"
    )]

    # 1. Time series if date column exists
    if date_cols and numeric_cols:
        for nc in numeric_cols[:2]:
            charts.append(ChartRecommendation(
                chart_type="line",
                title=f"{nc} over Time",
                x_column=date_cols[0],
                y_column=nc,
                aggregation="none",
            ))

    # 2. Categorical distributions
    for cat in categorical_cols[:3]:
        if numeric_cols:
            charts.append(ChartRecommendation(
                chart_type="bar",
                title=f"{cat} by {numeric_cols[0]}",
                x_column=cat,
                y_column=numeric_cols[0],
                aggregation="sum",
            ))
        charts.append(ChartRecommendation(
            chart_type="pie",
            title=f"{cat} Distribution",
            x_column=cat,
            y_column=numeric_cols[0] if numeric_cols else cat,
            aggregation="count",
        ))

    # 3. Correlation heatmap if enough numeric columns
    if len(numeric_cols) >= 3:
        charts.append(ChartRecommendation(
            chart_type="heatmap",
            title="Correlation Matrix",
            x_column=numeric_cols[0],
            y_column=numeric_cols[1],
            aggregation="none",
        ))

    # 4. Scatter for numeric pairs
    if len(numeric_cols) >= 2:
        charts.append(ChartRecommendation(
            chart_type="scatter",
            title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
            x_column=numeric_cols[0],
            y_column=numeric_cols[1],
            color_column=categorical_cols[0] if categorical_cols else None,
        ))

    # 5. Histograms
    for nc in numeric_cols[:3]:
        charts.append(ChartRecommendation(
            chart_type="histogram",
            title=f"{nc} Distribution",
            x_column=nc,
            y_column=nc,
        ))

    return build_dashboard(dataset, charts[:max_charts], title=title, filters=filters)


# ── Utilities ──────────────────────────────────────────────────────


def fig_to_base64(fig: go.Figure) -> str:
    """Convert a Plotly figure to a base64-encoded PNG string."""
    img_bytes = fig.to_image(format="png", width=800, height=500, scale=2)
    return base64.b64encode(img_bytes).decode("utf-8")


def dashboard_to_html(
    figures: list[tuple[go.Figure, str]], title: str = "Dashboard"
) -> str:
    """Generate a standalone HTML page with embedded Plotly charts."""
    import plotly.io as pio

    html_parts = [
        f"<!DOCTYPE html><html><head><title>{title}</title>",
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
        f"</head><body><h1>{title}</h1>",
    ]

    for i, (fig, sql) in enumerate(figures):
        fig_html = pio.to_html(fig, include_plotlyjs=False, full_html=False)
        html_parts.append(f'<div id="chart_{i}">{fig_html}</div>')
        if sql:
            html_parts.append(f'<details><summary>SQL</summary><pre><code>{sql}</code></pre></details>')

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def create_kpi_card(label: str, value: str, delta: str | None = None, icon: str = "📊") -> str:
    """Return an HTML KPI card."""
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """

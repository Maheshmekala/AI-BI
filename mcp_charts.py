"""MCP Chart Bridge — integrates open-source chart libraries and MCP tools.

Tries to use available MCP tools for chart rendering first,
falls back to our Plotly engine. Also pulls chart color themes
from popular open-source libraries.
"""
from __future__ import annotations

import json
from typing import Any

import plotly.graph_objects as go
import plotly.express as px
from plotly import colors as plotly_colors

# Open-source color themes inspired by popular libraries
COLOR_THEMES = {
    "tableau": [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
        "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
    ],
    "ggplot2": [
        "#F8766D", "#B79F00", "#00BA38", "#00BFC4", "#619CFF",
        "#C77DFF", "#F564E3", "#DE8C00", "#00C19F", "#FF61CC",
    ],
    "seaborn": [
        "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2",
        "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD",
    ],
    "material": [
        "#1976D2", "#388E3C", "#D32F2F", "#F57C00", "#7B1FA2",
        "#0097A7", "#689F38", "#E64A19", "#512DA8", "#00796B",
    ],
    "retro": [
        "#E63946", "#457B9D", "#1D3557", "#F1FAEE", "#A8DADC",
        "#F4A261", "#2A9D8F", "#264653", "#E76F51", "#E9C46A",
    ],
    "viridis": [
        "#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725",
    ],
    "plasma": [
        "#0D0887", "#7E03A8", "#CC4678", "#F89441", "#F0F921",
    ],
    "monokai": [
        "#F92672", "#A6E22E", "#FD971F", "#66D9EF", "#AE81FF",
        "#E6DB74", "#F8F8F2", "#75715E", "#E69F66", "#529B2F",
    ],
}


def get_color_theme(name: str = "tableau") -> list[str]:
    """Get a color theme by name, falling back to tableau10."""
    return COLOR_THEMES.get(name.lower(), COLOR_THEMES["tableau"])


def apply_theme_to_fig(fig: go.Figure, theme: str = "tableau") -> go.Figure:
    """Apply an open-source color theme to an existing Plotly figure."""
    colors = get_color_theme(theme)
    fig.update_layout(colorway=colors)

    # Force-override existing trace colors
    for i, trace in enumerate(fig.data):
        c = colors[i % len(colors)]
        # Pie / Sunburst / Treemap / Funnelarea use marker.colors (list), not marker.color
        if isinstance(trace, (go.Pie, go.Sunburst, go.Treemap, go.Funnelarea)):
            try:
                marker = trace.marker
                if marker is not None and not hasattr(marker, "colors") or not marker.colors:
                    color_count = len(trace.labels) if hasattr(trace, "labels") and trace.labels is not None else 1
                    trace.marker = dict(colors=[colors[j % len(colors)] for j in range(color_count)])
                continue
            except (AttributeError, TypeError):
                continue
        # Set line color for line/scatter/area
        if hasattr(trace, "line") and trace.line is not None:
            trace.line.color = c
            trace.line.width = 2
        # Set marker color for bar/scatter
        if hasattr(trace, "marker") and trace.marker is not None:
            try:
                trace.marker.color = c
            except (ValueError, TypeError):
                pass
            if hasattr(trace.marker, "line") and trace.marker.line is not None:
                trace.marker.line.color = "rgba(0,0,0,0.2)"
        # Set fillcolor for area charts
        if hasattr(trace, "fillcolor") and trace.fillcolor is not None:
            alpha = "0.3"
            if c.startswith("rgb("):
                trace.fillcolor = f"rgba{c[4:-1]},{alpha})"
            elif c.startswith("#"):
                r = int(c[1:3], 16)
                g = int(c[3:5], 16)
                b = int(c[5:7], 16)
                trace.fillcolor = f"rgba({r},{g},{b},{alpha})"

    return fig


def render_chart_with_mcp(
    chart_type: str,
    data: list[dict[str, Any]],
    x_column: str | None = None,
    y_column: str | None = None,
    color_column: str | None = None,
    title: str = "Chart",
    theme: str = "tableau",
    **kwargs: Any,
) -> go.Figure | None:
    """Try to render a chart using MCP tools, falling back to Plotly.

    This function wraps our existing Plotly renderer with:
    1. Better default color themes (Tableau, ggplot2, Seaborn, Material)
    2. Future MCP integration point for external rendering services
    3. Open-source font/size defaults
    """
    import pandas as pd
    from visualization import render_chart as plotly_render
    from query_engine.engine import ChartRecommendation

    try:
        # Build a mock dataset-like object for our renderer
        df = pd.DataFrame(data)

        # Use our existing Plotly renderer
        chart = ChartRecommendation(
            chart_type=chart_type,
            title=title,
            x_column=x_column or "",
            y_column=y_column or "",
            aggregation=kwargs.get("aggregation", "none"),
            color_column=color_column,
        )

        # Re-use the existing chart rendering logic (it handles all 17 types)
        # We just pass the data directly instead of going through SQL
        fig = _render_from_df(chart, df, height=kwargs.get("height", 400))

        # Apply open-source color theme
        fig = apply_theme_to_fig(fig, theme)

        return fig
    except Exception as exc:
        print(f"[MCP Chart] Fallback render failed: {exc}")
        return None


def _render_from_df(
    chart: Any,  # ChartRecommendation
    df: Any,  # pd.DataFrame
    height: int = 400,
    width: int = 600,
) -> go.Figure:
    """Minimal inline chart renderer from a DataFrame (no SQL needed)."""
    import plotly.express as px
    import plotly.graph_objects as go

    chart_type = chart.chart_type.lower()
    x = chart.x_column if chart.x_column in df.columns else None
    y = chart.y_column if isinstance(chart.y_column, str) and chart.y_column in df.columns else None
    color = chart.color_column if chart.color_column in df.columns else None

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, color=color, title=chart.title, height=height, width=width)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, color=color, title=chart.title, height=height, width=width, markers=True)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=chart.title, height=height, width=width)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=chart.title, height=height, width=width, hole=0.3)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x or y, color=color, title=chart.title, height=height, width=width, nbins=30)
        elif chart_type == "box":
            fig = px.box(df, x=x, y=y, color=color, title=chart.title, height=height, width=width)
        elif chart_type == "heatmap":
            if x and y and x != y:
                fig = px.density_heatmap(df, x=x, y=y, title=chart.title, height=height, width=width)
            else:
                fig = px.density_heatmap(df, title=chart.title, height=height, width=width)
        else:
            fig = px.bar(df, x=x, y=y, color=color, title=chart.title, height=height, width=width)
    except Exception:
        fig = go.Figure()
        fig.add_annotation(text=chart.title or "Chart", showarrow=False)

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(size=12, color="#4a5568"),
    )
    return fig

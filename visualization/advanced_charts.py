"""
Advanced chart types — Waterfall, Treemap, Gauge, Sankey, Parallel Coordinates, Candlestick.

All rendered using Plotly's graph_objects and express APIs.
These are called from the main visualization module when chart_type matches.
"""
from __future__ import annotations

from typing import Any, Optional

import plotly.express as px
import plotly.graph_objects as go


def render_waterfall(
    df: Any,
    x_column: str | None = None,
    y_column: str | None = None,
    title: str = "Waterfall Chart",
    height: int = 400,
    width: int = 600,
) -> go.Figure:
    """Render a waterfall chart."""
    x = x_column or (df.columns[0] if len(df.columns) > 0 else None)
    y = y_column or (df.columns[1] if len(df.columns) > 1 else df.columns[0])

    fig = go.Figure(go.Waterfall(
        x=df[x] if x and x in df.columns else df.index,
        y=df[y] if y and y in df.columns else df.iloc[:, 0].values,
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    fig.update_layout(
        title=title,
        height=height,
        width=width,
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


def render_treemap(
    df: Any,
    path_column: str | None = None,
    values_column: str | None = None,
    color_column: str | None = None,
    title: str = "Treemap",
    height: int = 400,
    width: int = 600,
) -> go.Figure:
    """Render a treemap chart."""
    path = path_column or (df.columns[0] if len(df.columns) > 0 else None)
    values = values_column or (df.columns[1] if len(df.columns) > 1 else None)

    fig = px.treemap(
        df,
        path=[path] if path else None,
        values=values,
        color=color_column,
        title=title,
        height=height,
        width=width,
    )
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
    return fig


def render_gauge(
    value: float = 50,
    title: str = "Gauge",
    min_val: float = 0,
    max_val: float = 100,
    thresholds: list[dict[str, Any]] | None = None,
    height: int = 300,
    width: int = 400,
) -> go.Figure:
    """Render a gauge/indicator chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={"text": title},
        delta={"reference": (max_val + min_val) / 2},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [min_val, max_val * 0.5], "color": "lightgray"},
                {"range": [max_val * 0.5, max_val * 0.75], "color": "gray"},
            ] if not thresholds else [
                {"range": [t.get("from", min_val), t.get("to", max_val)], "color": t.get("color", "gray")}
                for t in thresholds
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": max_val * 0.9,
            },
        },
    ))
    fig.update_layout(height=height, width=width, template="plotly_white")
    return fig


def render_sankey(
    df: Any,
    source_column: str | None = None,
    target_column: str | None = None,
    value_column: str | None = None,
    title: str = "Sankey Diagram",
    height: int = 500,
    width: int = 700,
) -> go.Figure:
    """Render a Sankey diagram."""
    src = source_column or (df.columns[0] if len(df.columns) > 0 else None)
    tgt = target_column or (df.columns[1] if len(df.columns) > 1 else None)
    val = value_column or (df.columns[2] if len(df.columns) > 2 else None)

    if not src or not tgt:
        fig = go.Figure()
        fig.add_annotation(text="Need source and target columns", showarrow=False)
        return fig

    # Build label list from unique values
    labels = list(set(df[src].tolist() + df[tgt].tolist()))
    label_to_idx = {label: i for i, label in enumerate(labels)}

    source_indices = [label_to_idx[s] for s in df[src]]
    target_indices = [label_to_idx[t] for t in df[tgt]]
    values = df[val].tolist() if val and val in df.columns else [1] * len(df)

    fig = go.Figure(go.Sankey(
        node=dict(pad=15, thickness=20, label=labels),
        link=dict(source=source_indices, target=target_indices, value=values),
    ))
    fig.update_layout(title=title, height=height, width=width, template="plotly_white")
    return fig


def render_parallel_coordinates(
    df: Any,
    dimensions: list[str] | None = None,
    color_column: str | None = None,
    title: str = "Parallel Coordinates",
    height: int = 500,
    width: int = 700,
) -> go.Figure:
    """Render a parallel coordinates plot."""
    num_df = df.select_dtypes(include=["number"])
    if num_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No numeric columns available", showarrow=False)
        return fig

    dims = dimensions or num_df.columns.tolist()
    color = color_column if color_column and color_column in dims else (dims[-1] if dims else None)
    other_dims = [d for d in dims if d != color]

    if not other_dims:
        fig = go.Figure()
        fig.add_annotation(text="Need at least 2 dimensions", showarrow=False)
        return fig

    fig = px.parallel_coordinates(
        df, dimensions=other_dims, color=color,
        title=title, height=height, width=width,
    )
    fig.update_layout(template="plotly_white")
    return fig


def render_candlestick(
    df: Any,
    date_column: str | None = None,
    open_column: str | None = None,
    high_column: str | None = None,
    low_column: str | None = None,
    close_column: str | None = None,
    title: str = "Candlestick Chart",
    height: int = 500,
    width: int = 700,
) -> go.Figure:
    """Render a candlestick chart."""
    cols = df.columns.tolist()
    open_c = open_column or (cols[0] if len(cols) > 0 else None)
    high_c = high_column or (cols[1] if len(cols) > 1 else cols[0])
    low_c = low_column or (cols[2] if len(cols) > 2 else cols[0])
    close_c = close_column or (cols[3] if len(cols) > 3 else cols[0])
    date_c = date_column or (cols[4] if len(cols) > 4 else None)

    if not all([open_c, high_c, low_c, close_c]):
        fig = go.Figure()
        fig.add_annotation(text="Need Open, High, Low, Close columns", showarrow=False)
        return fig

    fig = go.Figure(go.Candlestick(
        x=df[date_c] if date_c else df.index,
        open=df[open_c],
        high=df[high_c],
        low=df[low_c],
        close=df[close_c],
    ))
    fig.update_layout(
        title=title,
        height=height,
        width=width,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
    )
    return fig

"""Router — determines user intent and routes to the appropriate handler.

Classifies user questions as:
- chart_request: "Show me sales by region as a bar chart" → chart spec
- data_question: "What were our top products last quarter?" → SQL query
- general_chat: "What can I do with this data?" → LLM text response
"""
from __future__ import annotations
import re
from typing import Any


# Chart-related keywords that indicate a visualization request
CHART_KEYWORDS = [
    "chart", "graph", "plot", "visualize", "dashboard",
    "bar", "line", "pie", "scatter", "area", "histogram",
    "heatmap", "box", "violin", "waterfall", "treemap",
    "gauge", "sankey", "candlestick", "parallel coordinates",
    "show me", "display", "render",
]

# SQL/data-related keywords
DATA_KEYWORDS = [
    "select", "where", "group by", "order by", "join",
    "count", "sum", "average", "min", "max",
    "how many", "how much", "what is", "what are",
    "top", "bottom", "list", "find", "get", "calculate",
    "compare", "trend", "correlation", "correlate",
    "outlier", "distribution", "kpi", "metric",
]

# General chat keywords
CHAT_KEYWORDS = [
    "hello", "hi", "hey", "what can you do", "help",
    "explain", "how to", "what is this",
    "thank", "thanks",
]


class IntentRouter:
    """Routes user questions to the appropriate handler."""

    @staticmethod
    def route(question: str) -> str:
        """Determine the user's intent.

        Returns: "chart_request", "data_question", or "general_chat"
        """
        q = question.lower().strip()

        # Check for chart request patterns
        chart_score = sum(1 for kw in CHART_KEYWORDS if kw in q)
        data_score = sum(1 for kw in DATA_KEYWORDS if kw in q)
        chat_score = sum(1 for kw in CHAT_KEYWORDS if kw in q)

        # Chart requests often mention chart types
        if chart_score >= 2:
            return "chart_request"
        if chart_score >= 1 and data_score >= 1:
            return "chart_request"

        # Data questions often have query patterns
        if data_score >= 3:
            return "data_question"
        if data_score >= 2 and "?" in q and len(q) > 20:
            return "data_question"

        # General chat
        if chat_score >= 1 or len(q) < 15:
            return "general_chat"

        # Default: treat as data question if it ends with ?
        if q.endswith("?"):
            return "data_question"

        return "general_chat"

    @staticmethod
    def extract_chart_type(question: str) -> str | None:
        """Extract requested chart type from question."""
        q = question.lower()
        chart_types = [
            "bar", "line", "pie", "scatter", "area", "histogram",
            "heatmap", "box", "violin", "waterfall", "treemap",
            "gauge", "sankey", "candlestick", "parallel",
        ]
        for ct in chart_types:
            if ct in q:
                return ct
        return None

    @staticmethod
    def extract_columns(question: str, available_columns: list[str]) -> dict[str, Any]:
        """Try to extract relevant column names from the question."""
        q = question.lower()
        found = {"x": None, "y": None, "color": None}

        for col in available_columns:
            col_lower = col.lower().replace("_", " ")
            if col_lower in q:
                if found["x"] is None:
                    found["x"] = col
                elif found["y"] is None:
                    found["y"] = col
                else:
                    found["color"] = found.get("color") or col

        return found

"""REST endpoints for LLM-powered query — now generates SQL, not text analysis."""
from __future__ import annotations
import json
from typing import Any

from fastapi import APIRouter, HTTPException

from llm import get_llm, get_available_models, SYSTEM_PROMPTS, LLMMessage
from query_engine import QueryEngine
from query_engine.engine import ChartRecommendation
from visualization import render_chart, render_chart_figure
from data_sources.base import Dataset
from sql_engine.query_builder import QueryBuilder, FilterSpec
import plotly.io as pio

from backend.state import state
from backend.schemas import (
    QueryRequest, QueryResponse, ChartDataRequest, ChartDataResponse,
)

router = APIRouter()


def _chart_to_json(
    chart: ChartRecommendation, ds: Dataset,
    filters: list[FilterSpec] | None = None,
) -> dict[str, Any] | None:
    """Render a chart recommendation to a Plotly JSON dict + SQL."""
    try:
        fig, sql = render_chart(chart, ds, filters)
        fig_json = json.loads(pio.to_json(fig))
        return {
            "chart_type": chart.chart_type,
            "title": chart.title or "",
            "x_column": chart.x_column or "",
            "y_column": chart.y_column if chart.y_column is not None else "",
            "figure": fig_json,
            "sql": sql or "-- No SQL generated",
            "description": chart.description or "",
        }
    except Exception as exc:
        # Return a placeholder with error info instead of silently failing
        import plotly.graph_objects as go
        err_fig = go.Figure()
        err_fig.add_annotation(
            text=f"Chart error: {exc}<br>x={chart.x_column}, y={chart.y_column}",
            showarrow=False, font=dict(color="#e53e3e", size=12),
        )
        err_fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return {
            "chart_type": chart.chart_type,
            "title": f"⚠️ {(chart.title or 'Chart')} (error)",
            "x_column": chart.x_column or "",
            "y_column": chart.y_column if chart.y_column is not None else "",
            "figure": json.loads(pio.to_json(err_fig)),
            "sql": f"-- Error: {exc}\n-- x_column={chart.x_column}, y_column={chart.y_column}\n-- chart_type={chart.chart_type}",
            "description": chart.description or "",
        }


def _get_dataset(ds_id: str) -> Dataset:
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    return ds


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a natural language question about a dataset — generates SQL.

    The LLM now generates SQL queries instead of text analysis.
    The SQL is executed against DuckDB and the results rendered as charts.
    """
    ds = _get_dataset(req.dataset_id)

    try:
        # Build query engine with optional model override
        engine = QueryEngine()
        if req.model and req.provider:
            engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

        result = engine.query(
            question=req.question,
            dataset=ds,
            generate_charts=req.generate_charts,
            system_prompt_key=req.system_prompt_key,
        )

        if result.error:
            return QueryResponse(
                answer=result.answer,
                error=result.error,
                metadata=result.metadata,
            )

        # Render charts to Plotly JSON
        rendered = []
        for chart in result.charts:
            fig_data = _chart_to_json(chart, ds)
            if fig_data:
                rendered.append(fig_data)

        # Return the SQL queries used
        sql_queries = [r.get("sql", "") for r in rendered if r and r.get("sql")]

        return QueryResponse(
            answer=result.answer,
            charts=[{
                "chart_type": c.chart_type,
                "title": c.title or "",
                "x_column": c.x_column or "",
                "y_column": c.y_column if c.y_column is not None else "",
                "aggregation": c.aggregation or "none",
                "color_column": c.color_column,
                "description": c.description or "",
            } for c in result.charts],
            rendered_charts=rendered,
            sql="\n\n".join(sql_queries) if sql_queries else None,
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Stream a natural language query response via SSE (SQL-generated)."""
    from fastapi.responses import StreamingResponse

    ds = _get_dataset(req.dataset_id)

    engine = QueryEngine()
    if req.model and req.provider:
        engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

    async def event_stream():
        try:
            system = SYSTEM_PROMPTS.get(req.system_prompt_key, SYSTEM_PROMPTS["data_analyst"])
            context = engine._build_dataset_context(ds)

            user_parts = [context, f"User question: {req.question}"]
            if req.generate_charts:
                user_parts.append(
                    "Generate SQL queries in ```sql blocks. "
                    "I will execute them against the database."
                )

            user_prompt = "\n\n".join(user_parts)
            messages = [
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user_prompt),
            ]

            # Use streaming from the LLM provider
            if engine.llm.supports_streaming:
                full_text = ""
                for chunk in engine.llm.chat_stream(messages):
                    if chunk:
                        full_text += chunk
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

                # After streaming, extract SQL and render charts
                if req.generate_charts:
                    non_stream_result = engine.query(
                        question=req.question,
                        dataset=ds,
                        generate_charts=True,
                        system_prompt_key=req.system_prompt_key,
                    )
                    rendered = []
                    for chart in non_stream_result.charts:
                        fig_data = _chart_to_json(chart, ds)
                        if fig_data:
                            rendered.append(fig_data)

                    if rendered:
                        yield f"data: {json.dumps({'type': 'charts', 'content': rendered})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            else:
                # Non-streaming fallback
                result = engine.query(
                    question=req.question,
                    dataset=ds,
                    generate_charts=req.generate_charts,
                    system_prompt_key=req.system_prompt_key,
                )
                yield f"data: {json.dumps({'type': 'text', 'content': result.answer})}\n\n"

                rendered = []
                for chart in result.charts:
                    fig_data = _chart_to_json(chart, ds)
                    if fig_data:
                        rendered.append(fig_data)
                if rendered:
                    yield f"data: {json.dumps({'type': 'charts', 'content': rendered})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/render-chart")
async def render_chart_endpoint(req: ChartDataRequest):
    """Render a single chart recommendation from a dataset."""
    ds = _get_dataset(req.dataset_id)
    try:
        chart = ChartRecommendation(
            chart_type=req.chart_type,
            title="Chart",
            x_column=req.x_column or "",
            y_column=req.y_column or "",
            aggregation=req.aggregation or "none",
            color_column=req.color_column,
        )
        fig, sql = render_chart(chart, ds)
        fig_json = json.loads(pio.to_json(fig))
        return {"figure_json": fig_json, "sql": sql}
    except Exception as exc:
        return {"error": str(exc)}

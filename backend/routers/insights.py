"""REST endpoints for automated data insights — SQL-powered."""
from __future__ import annotations
import json

from fastapi import APIRouter, HTTPException

from insights import InsightsEngine
from llm import get_llm
from visualization import render_chart, auto_dashboard
from query_engine import QueryEngine
from sql_engine.query_builder import QueryBuilder

from backend.state import state
from backend.schemas import InsightRequest, InsightsResponse, DashboardRequest

router = APIRouter()


@router.post("/insights", response_model=InsightsResponse)
async def run_insights(req: InsightRequest):
    """Run full statistical + LLM analysis on a dataset — SQL-powered."""
    ds = state.get_dataset(req.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        engine = InsightsEngine()
        if req.model and req.provider:
            engine.llm = get_llm(model_name=req.model, provider_name=req.provider)
        else:
            engine.llm = get_llm()

        analysis = engine.analyze(ds)

        return InsightsResponse(
            overview=analysis.get("overview", {}),
            statistical=analysis.get("statistical", {}),
            correlations=analysis.get("correlations", {}),
            outliers=analysis.get("outliers", {}),
            trends=analysis.get("trends", []),
            kpis=analysis.get("kpis", []),
            llm_insights=analysis.get("llm_insights", ""),
        )

    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/generate-dashboard")
async def generate_dashboard(req: DashboardRequest):
    """Auto-generate a dashboard from a dataset — SQL-powered."""
    ds = state.get_dataset(req.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        import plotly.io as pio
        from backend.schemas import FilterSpec

        filter_specs = []
        if req.filters:
            from sql_engine.query_builder import FilterSpec as QBFilter
            for f in req.filters:
                filter_specs.append(QBFilter(
                    column=f.column,
                    operator=f.operator,
                    value=f.value,
                    values=f.values or [],
                ))

        if req.use_llm:
            engine = QueryEngine()
            if req.model and req.provider:
                engine.llm = get_llm(model_name=req.model, provider_name=req.provider)

            result = engine.query(
                question="Design a comprehensive dashboard for this dataset. "
                         "Suggest the most informative visualizations.",
                dataset=ds,
                generate_charts=True,
                system_prompt_key="dashboard_designer",
            )
            charts = result.charts[:req.max_charts]
            figures_and_sql = [render_chart(chart, ds, filter_specs) for chart in charts]
        else:
            figures_and_sql = auto_dashboard(ds, title=ds.name, max_charts=req.max_charts, filters=filter_specs)

        from visualization import render_chart
        chart_data = []
        sqls = []
        for fig, sql in figures_and_sql:
            chart_data.append(json.loads(pio.to_json(fig)))
            if sql:
                sqls.append(sql)

        return {"charts": chart_data, "sqls": sqls}

    except Exception as exc:
        raise HTTPException(500, str(exc))

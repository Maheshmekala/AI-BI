"""REST endpoints for listing, managing, and querying datasets — SQL-powered."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.state import state
from backend.schemas import (
    DatasetInfo, DatasetDataResponse, ChartDataRequest, ChartDataResponse,
    HierarchyInfo, HierarchyLevel,
)
from sql_engine.query_builder import QueryBuilder, FilterSpec
from sql_engine import _qi
from visualization import render_chart_figure
import plotly.io as pio
import json

router = APIRouter()


@router.get("/datasets")
async def list_datasets():
    """List all loaded datasets."""
    return state.list_datasets()


@router.get("/datasets/{ds_id}", response_model=DatasetInfo)
async def get_dataset(ds_id: str):
    """Get full details and preview for a dataset."""
    info = state.dataset_info(ds_id)
    if info is None:
        raise HTTPException(404, "Dataset not found")
    return DatasetInfo(**info)


@router.get("/datasets/{ds_id}/data", response_model=DatasetDataResponse)
async def get_dataset_data(ds_id: str, limit: int = 100000):
    """Get the full dataset data as JSON rows (for client-side operations)."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    try:
        rows = ds.query(f"SELECT * FROM {_qi(ds.table_name)} LIMIT {limit}")
        total = ds.row_count
        return DatasetDataResponse(rows=rows, total_count=total)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/datasets/{ds_id}/chart-data", response_model=ChartDataResponse)
async def get_chart_data(ds_id: str, req: ChartDataRequest):
    """Execute a chart spec and return the aggregated data + SQL.

    This is the core endpoint for the SQL-first architecture.
    Frontend sends the chart spec, backend generates & executes SQL,
    returns only the aggregated results.
    """
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        qb = QueryBuilder()
        filter_specs = [
            FilterSpec(column=f.column, operator=f.operator, value=f.value, values=f.values)
            for f in req.filters
        ]

        sql, params = qb.build_chart_sql(
            table=ds.table_name,
            chart_type=req.chart_type,
            x_column=req.x_column,
            y_column=req.y_column if isinstance(req.y_column, str) else (req.y_column[0] if req.y_column else None),
            aggregation=req.aggregation,
            color_column=req.color_column,
            filters=filter_specs,
            limit=req.limit,
        )

        data = ds.query(sql)
        return ChartDataResponse(data=data, sql=sql, row_count=len(data))

    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/datasets/{ds_id}/hierarchies")
async def get_hierarchies(ds_id: str):
    """Auto-detect hierarchical columns in a dataset."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    hierarchies = []
    cols = ds.columns_info

    # ── Detect date hierarchies ──
    date_cols = [c["name"] for c in cols if c["dtype"].upper() in (
        "DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "DATETIME"
    )]
    for dc in date_cols[:2]:
        hierarchies.append(HierarchyInfo(
            name=f"{dc} (Date Hierarchy)",
            type="date",
            levels=[
                HierarchyLevel(column=f"YEAR({dc})", label="Year", cardinality=0),
                HierarchyLevel(column=f"QUARTER({dc})", label="Quarter", cardinality=0),
                HierarchyLevel(column=f"MONTH({dc})", label="Month", cardinality=0),
                HierarchyLevel(column=dc, label="Day", cardinality=0),
            ],
        ))

    # ── Detect geographic/categorical hierarchies ──
    cat_cols = [c["name"] for c in cols if c["dtype"].upper() in (
        "VARCHAR", "TEXT", "CHAR", "STRING"
    )]

    # Look for common geographic patterns
    geo_keywords = ["country", "region", "state", "city", "province", "district", "zip", "postal"]
    geo_cols = [c for c in cat_cols if any(kw in c.lower() for kw in geo_keywords)]

    if len(geo_cols) >= 2:
        hierarchies.append(HierarchyInfo(
            name="Geographic Hierarchy",
            type="geographic",
            levels=[
                HierarchyLevel(column=c, label=c.replace("_", " ").title(), cardinality=0)
                for c in geo_cols[:5]
            ],
        ))

    # ── Detect 1:N relationships between categorical columns ──
    if len(cat_cols) >= 2 and not geo_cols:
        # Use first two cat cols as a simple hierarchy
        hierarchies.append(HierarchyInfo(
            name="Categorical Hierarchy",
            type="categorical",
            levels=[
                HierarchyLevel(column=c, label=c.replace("_", " ").title(), cardinality=0)
                for c in cat_cols[:5]
            ],
        ))

    return hierarchies


@router.delete("/datasets/{ds_id}")
async def delete_dataset(ds_id: str):
    """Remove a dataset and drop its DuckDB table."""
    from backend.state import state
    if state.remove_dataset(ds_id):
        return {"status": "ok", "message": "Dataset removed"}
    raise HTTPException(404, "Dataset not found")

"""Instant BI — FastAPI Backend (SQL-Powered).

Provides a REST API that wraps the DuckDB SQL engine + RAG pipeline.
Every operation generates SQL queries executed by DuckDB.
"""
from __future__ import annotations
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    datasets, query, insights, models, settings, sources,
    calculations, rag,
)
# Import optional routers (they may not exist yet)
try:
    from backend.routers import parameters as parameters_router
    HAS_PARAMETERS = True
except ImportError:
    HAS_PARAMETERS = False

try:
    from backend.routers import blending as blending_router
    HAS_BLENDING = True
except ImportError:
    HAS_BLENDING = False

try:
    from backend.routers import stories as stories_router
    HAS_STORIES = True
except ImportError:
    HAS_STORIES = False

app = FastAPI(
    title="Instant BI API",
    version="3.0.0",
    description="SQL-powered REST API for Instant BI — chat with your data",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routers (always available)
app.include_router(sources.router, prefix="/api", tags=["Sources"])
app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(insights.router, prefix="/api", tags=["Insights"])
app.include_router(models.router, prefix="/api", tags=["Models"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(calculations.router, prefix="/api", tags=["Calculations"])
app.include_router(rag.router, prefix="/api", tags=["RAG"])

# Optional routers
if HAS_PARAMETERS:
    app.include_router(parameters_router.router, prefix="/api", tags=["Parameters"])
if HAS_BLENDING:
    app.include_router(blending_router.router, prefix="/api", tags=["Blending"])
if HAS_STORIES:
    app.include_router(stories_router.router, prefix="/api", tags=["Stories"])


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": "Instant BI",
        "version": "3.0.0",
        "engine": "duckdb",
        "features": {
            "rag": True,
            "calculated_fields": True,
            "cross_filtering": True,
            "drill_down": True,
            "blending": HAS_BLENDING,
            "stories": HAS_STORIES,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

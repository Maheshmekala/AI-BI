"""REST endpoint for RAG-powered natural language → SQL queries."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.state import state
from backend.schemas import RAGQueryRequest, RAGQueryResponse
from rag.retriever import Retriever
from rag.llm_sql import LLMtoSQL
from rag.semantic_cache import SemanticCache
from rag.router import IntentRouter
from rag.schema_index import SchemaIndex
from llm import get_llm

router = APIRouter()


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(req: RAGQueryRequest):
    """Natural language → SQL via RAG.

    Takes a question in natural language, retrieves relevant schema context,
    generates SQL via LLM, executes it, and returns results + SQL.
    """
    ds = state.get_dataset(req.dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    # Get or create LLM
    llm = None
    if req.model and req.provider:
        llm = get_llm(model_name=req.model, provider_name=req.provider)

    # Build RAG components
    schema_index = SchemaIndex(state.engine)
    schema_index.index_dataset(ds)

    retriever = Retriever(schema_index=schema_index)
    cache = SemanticCache()

    llm_to_sql = LLMtoSQL(
        llm=llm,
        sql_engine=state.engine,
        retriever=retriever,
        cache=cache,
    )

    # Route intent
    intent = IntentRouter.route(req.question)

    if intent == "chart_request":
        # Extract chart type and generate chart spec
        from rag.router import IntentRouter as IR
        chart_type = IR.extract_chart_type(req.question)
        columns = [c["name"] for c in ds.columns_info]
        found = IR.extract_columns(req.question, columns)

        from sql_engine.query_builder import QueryBuilder
        qb = QueryBuilder()
        sql, params = qb.build_chart_sql(
            table=ds.table_name,
            chart_type=chart_type or "bar",
            x_column=found.get("x"),
            y_column=found.get("y"),
            aggregation="sum",
            color_column=found.get("color"),
            limit=5000,
        )

        try:
            data = ds.query(sql, params)
            return RAGQueryResponse(
                answer=f"Generated {chart_type or 'bar'} chart",
                sql=sql,
                chart_data=data,
                chart_spec={
                    "chart_type": chart_type or "bar",
                    "x_column": found.get("x"),
                    "y_column": found.get("y"),
                    "color_column": found.get("color"),
                },
            )
        except Exception as exc:
            return RAGQueryResponse(
                answer=f"Could not generate chart: {exc}",
                sql=sql,
                error=str(exc),
            )

    elif intent == "data_question":
        result = llm_to_sql.generate_sql(req.question, dataset_name=ds.name)
        return RAGQueryResponse(
            answer=result.get("explanation", "") or "Query executed successfully",
            sql=result.get("sql"),
            chart_data=result.get("data"),
            error=result.get("error"),
        )

    else:
        # General chat — use LLM directly
        if llm:
            from llm import LLMMessage

            summary = ds.summary()
            context = f"Dataset: {ds.name}\nRows: {summary['rows']}\nColumns: {summary['columns']}\n{summary['column_names']}"
            messages = [
                LLMMessage(role="system", content="You are a helpful BI assistant."),
                LLMMessage(role="user", content=f"{req.question}\n\nCurrent dataset: {context}"),
            ]
            response = llm.chat(messages)
            return RAGQueryResponse(answer=response.content)
        else:
            return RAGQueryResponse(answer="I'm a BI assistant. Try asking about your data!")


@router.post("/rag/index/{ds_id}")
async def index_dataset(ds_id: str):
    """Re-index a dataset for RAG retrieval."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    schema_index = SchemaIndex(state.engine)
    result = schema_index.index_dataset(ds)

    return {
        "status": "ok",
        "dataset": ds.name,
        "table": ds.table_name,
        "columns": len(result.get("columns", [])),
        "row_count": ds.row_count,
    }

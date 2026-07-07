"""Pydantic schemas for the Instant BI API — expanded for SQL-powered features."""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Dataset ──

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    unique_count: int = 0
    sample_values: list[Any] = []


class DatasetInfo(BaseModel):
    id: str
    name: str
    source_type: str = ""
    description: str = ""
    row_count: int = 0
    column_count: int = 0
    columns: list[ColumnInfo] = []
    preview_rows: list[dict[str, Any]] = []
    summary_stats: dict[str, Any] = {}


class DatasetListItem(BaseModel):
    id: str
    name: str
    source_type: str
    row_count: int
    column_count: int


# ── Dataset Data (for cross-filtering / full data access) ──

class DatasetDataResponse(BaseModel):
    rows: list[dict[str, Any]]
    total_count: int


# ── Upload / DB Connect ──

class UploadResponse(BaseModel):
    dataset: DatasetInfo
    message: str = ""


class DBConnectRequest(BaseModel):
    db_type: str = Field(..., pattern="^(PostgreSQL|MySQL|SQLite|Other)$")
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = "postgres"
    password: str = ""
    connection_string: str = ""
    connection_name: str = "My DB"


class DBConnectResponse(BaseModel):
    dataset: DatasetInfo
    message: str = ""


# ── Filter Spec ──

class FilterSpec(BaseModel):
    column: str
    operator: str = "in"  # in, not_in, eq, neq, gt, gte, lt, lte, between, contains
    value: Any = None
    values: list[Any] = []


# ── Chart Data (SQL-backed) ──

class ChartDataRequest(BaseModel):
    dataset_id: str
    chart_type: str = "bar"
    x_column: str | None = None
    y_column: str | list[str] | None = None
    aggregation: str = "none"
    color_column: str | None = None
    filters: list[FilterSpec] = []
    limit: int = 5000


class ChartDataResponse(BaseModel):
    data: list[dict[str, Any]]
    sql: str
    row_count: int


# ── Query ──

class QueryRequest(BaseModel):
    dataset_id: str
    question: str
    model: str | None = None
    provider: str | None = None
    system_prompt_key: str = "data_analyst"
    generate_charts: bool = True


class ChartRecommendation(BaseModel):
    chart_type: str = "bar"
    title: str = ""
    x_column: str = ""
    y_column: str | list[str] = ""
    aggregation: str = "none"
    color_column: str | None = None
    description: str = ""


class QueryResponse(BaseModel):
    answer: str = ""
    charts: list[ChartRecommendation] = []
    rendered_charts: list[dict[str, Any]] = []
    sql: str | None = None  # The SQL query executed
    error: str | None = None
    metadata: dict[str, Any] = {}


# ── Dashboard ──

class DashboardRequest(BaseModel):
    dataset_id: str
    max_charts: int = 6
    use_llm: bool = False
    model: str | None = None
    provider: str | None = None
    filters: list[FilterSpec] = []


class InsightRequest(BaseModel):
    dataset_id: str
    model: str | None = None
    provider: str | None = None


class DashboardResponse(BaseModel):
    charts: list[dict[str, Any]]
    sqls: list[str] = []  # SQL queries for each chart
    error: str | None = None


# ── RAG Query ──

class RAGQueryRequest(BaseModel):
    dataset_id: str
    question: str
    model: str | None = None
    provider: str | None = None


class RAGQueryResponse(BaseModel):
    answer: str = ""
    sql: str | None = None
    chart_data: list[dict[str, Any]] | None = None
    chart_spec: dict[str, Any] | None = None
    error: str | None = None


# ── Insights ──

class InsightsResponse(BaseModel):
    overview: dict[str, Any] = {}
    statistical: dict[str, Any] = {}
    correlations: dict[str, Any] = {}
    outliers: dict[str, Any] = {}
    trends: list[dict[str, Any]] = []
    kpis: list[dict[str, Any]] = []
    llm_insights: str = ""
    sql_queries: dict[str, str] = {}  # SQL queries used for each analysis
    error: str | None = None


# ── Models ──

class ModelInfo(BaseModel):
    id: str
    provider: str
    name: str


# ── Calculated Fields ──

class CalculatedFieldCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    expression: str


class CalculatedFieldPreview(BaseModel):
    expression: str
    limit: int = 10


class CalculatedFieldPreviewResponse(BaseModel):
    column_name: str
    values: list[Any]


class CalculatedFieldValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []


class CalculatedFieldInfo(BaseModel):
    name: str
    expression: str
    view_name: str
    created_at: str = ""


# ── Parameters ──

class ParameterCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type: str = "number"  # number, string, date, list
    default_value: Any = None
    current_value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    valid_values: list[Any] | None = None
    step: float = 1.0


class ParameterValueUpdate(BaseModel):
    value: Any


class ParameterInfo(BaseModel):
    name: str
    type: str
    default_value: Any = None
    current_value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    valid_values: list[Any] | None = None
    step: float = 1.0


# ── Hierarchies ──

class HierarchyLevel(BaseModel):
    column: str
    label: str
    cardinality: int = 0


class HierarchyInfo(BaseModel):
    name: str
    levels: list[HierarchyLevel]
    type: str = "categorical"  # date, geographic, categorical


# ── Data Blending ──

class BlendRequest(BaseModel):
    dataset_ids: list[str]
    joins: list[dict[str, Any]] = []
    blend_type: str = "join"  # join, union
    join_type: str = "left"  # left, inner, outer, cross
    output_name: str = "Blended Dataset"


class JoinSuggestion(BaseModel):
    left_column: str
    right_column: str
    left_dataset_id: str
    right_dataset_id: str
    similarity: float = 0.0


# ── Stories ──

class StoryPoint(BaseModel):
    title: str
    description: str = ""
    chart_configs: list[dict[str, Any]] = []
    filter_state: list[FilterSpec] = []
    parameter_values: dict[str, Any] = {}
    annotations: list[dict[str, Any]] = []


class StoryCreate(BaseModel):
    title: str
    dataset_id: str
    points: list[StoryPoint] = []


class StoryInfo(BaseModel):
    id: str
    title: str
    dataset_id: str
    points: list[StoryPoint] = []
    created_at: str = ""


# ── Settings ──

class SettingsResponse(BaseModel):
    app_name: str = "Instant BI"
    debug: bool = False
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    max_upload_size_mb: int = 200
    cache_ttl_seconds: int = 3600
    available_providers: list[str] = []


class SettingsUpdateRequest(BaseModel):
    groq_default_model: str | None = None
    openai_default_model: str | None = None
    anthropic_default_model: str | None = None
    google_default_model: str | None = None
    max_upload_size_mb: int | None = None
    cache_ttl_seconds: int | None = None


# ── Export ──

class ExportRequest(BaseModel):
    charts: list[dict[str, Any]]
    sqls: list[str] = []
    title: str = "Dashboard Export"
    format: str = "html"  # html, png, pdf

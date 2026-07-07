// ── Dataset Types ──

export interface DatasetInfo {
  id: string;
  name: string;
  source_type: string;
  description: string;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  preview_rows: Record<string, unknown>[];
  summary_stats: Record<string, unknown>;
}

export interface DatasetListItem {
  id: string;
  name: string;
  source_type: string;
  row_count: number;
  column_count: number;
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
  sample_values: unknown[];
}

export interface DatasetDataResponse {
  rows: Record<string, unknown>[];
  total_count: number;
}

// ── Filter Spec ──

export interface FilterSpec {
  column: string;
  operator: 'in' | 'not_in' | 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'contains';
  value?: unknown;
  values?: unknown[];
}

// ── Chart Types ──

export interface ChartRecommendation {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string | string[];
  aggregation: string;
  color_column?: string;
  description?: string;
}

export interface RenderedChart {
  chart_type: string;
  title: string;
  x_column: string;
  y_column: string | string[];
  figure: PlotlyFigure;
  sql?: string;
  description?: string;
}

export interface PlotlyFigure {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export interface ChartDataResponse {
  data: Record<string, unknown>[];
  sql: string;
  row_count: number;
}

export interface ChartDataRequest {
  dataset_id: string;
  chart_type: string;
  x_column?: string;
  y_column?: string | string[];
  aggregation?: string;
  color_column?: string;
  filters?: FilterSpec[];
  limit?: number;
}

// ── Query Types ──

export interface QueryResponse {
  answer: string;
  charts: ChartRecommendation[];
  rendered_charts: RenderedChart[];
  sql?: string;
  error?: string;
  metadata: Record<string, unknown>;
}

export interface QueryRequest {
  dataset_id: string;
  question: string;
  model?: string;
  provider?: string;
  system_prompt_key?: string;
  generate_charts?: boolean;
}

// ── RAG Types ──

export interface RAGQueryRequest {
  dataset_id: string;
  question: string;
  model?: string;
  provider?: string;
}

export interface RAGQueryResponse {
  answer: string;
  sql?: string;
  chart_data?: Record<string, unknown>[];
  chart_spec?: Record<string, unknown>;
  error?: string;
}

// ── Insights Types ──

export interface InsightsResponse {
  overview: Record<string, unknown>;
  statistical: Record<string, unknown>;
  correlations: Record<string, unknown>;
  outliers: Record<string, unknown>;
  trends: TrendInfo[];
  kpis: KpiInfo[];
  llm_insights: string;
  sql_queries?: Record<string, string>;
  error?: string;
}

export interface TrendInfo {
  column: string;
  trend: string;
  slope: number;
  r_squared: number;
  significant: boolean;
}

export interface KpiInfo {
  label: string;
  value: string;
  delta?: string;
  icon?: string;
  direction?: string;
  is_good?: boolean;
}

// ── Calculated Fields ──

export interface CalculatedField {
  name: string;
  expression: string;
  view_name: string;
}

export interface CalculatedFieldCreate {
  name: string;
  expression: string;
}

export interface CalculatedFieldPreviewResponse {
  column_name: string;
  values: unknown[];
  error?: string[];
}

export interface CalculatedFieldValidateResponse {
  valid: boolean;
  errors: string[];
}

// ── Hierarchies ──

export interface HierarchyLevel {
  column: string;
  label: string;
  cardinality: number;
}

export interface HierarchyInfo {
  name: string;
  levels: HierarchyLevel[];
  type: string;
}

// ── Parameters ──

export interface ParameterInfo {
  name: string;
  type: string;
  default_value?: unknown;
  current_value?: unknown;
  min_value?: number;
  max_value?: number;
  valid_values?: unknown[];
  step?: number;
}

// ── Model Types ──

export interface ModelInfo {
  id: string;
  provider: string;
  name: string;
}

// ── Settings Types ──

export interface SettingsInfo {
  app_name: string;
  debug: boolean;
  groq_api_key: string;
  openai_api_key: string;
  anthropic_api_key: string;
  google_api_key: string;
  max_upload_size_mb: number;
  cache_ttl_seconds: number;
  available_providers: string[];
}

// ── SSE Types ──

export interface SSEEvent {
  type: 'text' | 'charts' | 'error' | 'done';
  content: unknown;
}

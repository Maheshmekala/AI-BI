const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: isFormData ? {} : { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((body as Record<string, unknown>).detail as string || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ── Upload ──
  uploadFile: (file: File, autoClean = true, sep = ',') => {
    const form = new FormData();
    form.append('file', file);
    form.append('auto_clean', String(autoClean));
    form.append('sep', sep);
    return request<{ dataset: import('../types').DatasetInfo; message: string }>('/upload', {
      method: 'POST',
      body: form,
    });
  },

  // ── Database ──
  connectDb: (config: Record<string, unknown>) =>
    request<{ dataset: import('../types').DatasetInfo; message: string }>('/connect-db', {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  // ── Datasets ──
  listDatasets: () =>
    request<import('../types').DatasetListItem[]>('/datasets'),

  getDataset: (id: string) =>
    request<import('../types').DatasetInfo>(`/datasets/${id}`),

  getDatasetData: (id: string, limit = 100000) =>
    request<import('../types').DatasetDataResponse>(`/datasets/${id}/data?limit=${limit}`),

  deleteDataset: (id: string) =>
    request<{ status: string }>(`/datasets/${id}`, { method: 'DELETE' }),

  getHierarchies: (id: string) =>
    request<import('../types').HierarchyInfo[]>(`/datasets/${id}/hierarchies`),

  // ── Chart Data (SQL-powered) ──
  getChartData: (datasetId: string, req: import('../types').ChartDataRequest) =>
    request<import('../types').ChartDataResponse>(`/datasets/${datasetId}/chart-data`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  // ── Query ──
  query: (payload: import('../types').QueryRequest) =>
    request<import('../types').QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── Direct Chart Render (no LLM) ──
  renderChartDirect: (req: import('../types').ChartDataRequest) =>
    request<{ figure_json: Record<string, unknown>; sql: string }>('/render-chart', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  // ── Insights ──
  runInsights: (payload: { dataset_id: string; model?: string; provider?: string }) =>
    request<import('../types').InsightsResponse>('/insights', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── Dashboard ──
  generateDashboard: (payload: Record<string, unknown>) =>
    request<{ charts: Record<string, unknown>[]; sqls: string[] }>('/generate-dashboard', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // ── RAG ──
  ragQuery: (payload: import('../types').RAGQueryRequest) =>
    request<import('../types').RAGQueryResponse>('/rag/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  indexForRag: (datasetId: string) =>
    request<{ status: string }>(`/rag/index/${datasetId}`, { method: 'POST' }),

  // ── Calculated Fields ──
  listCalculatedFields: (datasetId: string) =>
    request<import('../types').CalculatedField[]>(`/datasets/${datasetId}/calculated-fields`),

  createCalculatedField: (datasetId: string, field: import('../types').CalculatedFieldCreate) =>
    request<import('../types').CalculatedField>(`/datasets/${datasetId}/calculated-fields`, {
      method: 'POST',
      body: JSON.stringify(field),
    }),

  deleteCalculatedField: (datasetId: string, name: string) =>
    request<{ status: string }>(`/datasets/${datasetId}/calculated-fields/${name}`, { method: 'DELETE' }),

  previewCalculatedField: (datasetId: string, expression: string, limit = 10) =>
    request<import('../types').CalculatedFieldPreviewResponse>(`/datasets/${datasetId}/calculated-fields/preview`, {
      method: 'POST',
      body: JSON.stringify({ expression, limit }),
    }),

  validateCalculatedField: (datasetId: string, name: string, expression: string) =>
    request<import('../types').CalculatedFieldValidateResponse>(`/datasets/${datasetId}/calculated-fields/validate`, {
      method: 'POST',
      body: JSON.stringify({ name, expression }),
    }),

  listSupportedFunctions: () =>
    request<Record<string, string>>('/calculated-functions'),

  // ── Models ──
  listModels: () =>
    request<import('../types').ModelInfo[]>('/models'),

  // ── Settings ──
  getSettings: () =>
    request<import('../types').SettingsInfo>('/settings'),

  updateSettings: (payload: Partial<import('../types').SettingsInfo>) =>
    request<import('../types').SettingsInfo>('/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};

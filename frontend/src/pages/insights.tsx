import { api } from '../lib/api';
import { ChartWithSQL } from '../components/charts/chart-with-sql';
import type { DatasetInfo, InsightsResponse } from '../types';
import { useState } from 'react';

interface InsightsPageProps {
  dataset: DatasetInfo;
  insights: ReturnType<typeof import('../hooks/use-insights').useInsights>;
}

export function InsightsPage({ dataset }: InsightsPageProps) {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const res: InsightsResponse = await api.runInsights({ dataset_id: dataset.id });
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">💡</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Auto Insights & KPIs</h1>
          <p className="text-sm text-[#718096] m-0">SQL-powered statistical analysis — each insight shows its query</p>
        </div>
      </div>

      <button
        onClick={runAnalysis}
        disabled={loading}
        className="mb-6 px-8 py-3 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 shadow-sm transition-all active:scale-95"
      >
        {loading ? 'Analyzing...' : '🔍 Run Full Analysis (SQL)'}
      </button>

      {error && (
        <div className="p-4 mb-4 rounded-xl bg-[#fff5f5] border border-[#e8ecf0] text-sm text-[#e53e3e]">{error}</div>
      )}

      {!data && !loading && (
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">
          {dataset ? 'Click "Run Full Analysis" to discover insights via SQL' : 'Upload data first'}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="flex gap-1.5">
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}

      {data && (
        <div className="space-y-6">
          {/* KPIs */}
          {data.kpis.length > 0 && (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
              <h2 className="text-lg font-bold text-[#1a202c] mb-3">🎯 Key Performance Indicators</h2>
              <div className="grid grid-cols-5 gap-3">
                {data.kpis.map((kpi, i) => (
                  <div key={i} className="text-center p-3 rounded-lg bg-[#f7fafc] border border-[#e8ecf0]">
                    <p className="text-2xl mb-1">{kpi.icon || '📊'}</p>
                    <p className="text-xs text-[#718096] mb-1">{kpi.label}</p>
                    <p className="text-xl font-bold text-[#1a202c]">{kpi.value}</p>
                    {kpi.delta && (
                      <p className={`text-xs mt-1 ${(kpi.direction === 'up' || kpi.is_good) ? 'text-[#38a169]' : 'text-[#e53e3e]'}`}>
                        {kpi.delta}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Overview */}
          <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
            <h2 className="text-lg font-bold text-[#1a202c] mb-3">📋 Dataset Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Rows', value: data.overview?.rows ?? '-' },
                { label: 'Columns', value: data.overview?.columns ?? '-' },
                { label: 'Completeness', value: data.overview?.completeness != null ? `${data.overview.completeness}%` : '-' },
                { label: 'Duplicates', value: data.overview?.duplicate_rows ?? '-' },
              ].map((stat, i) => (
                <div key={i} className="text-center">
                  <p className="text-[10px] font-semibold text-[#718096] uppercase">{stat.label}</p>
                  <p className="text-xl font-bold text-[#1a202c]">{stat.value}</p>
                </div>
              ))}
            </div>
            {/* SQL query for overview */}
            <details className="mt-3">
              <summary className="text-xs text-[#718096] cursor-pointer hover:text-[#1a202c]">📝 View SQL</summary>
              <pre className="mt-2 text-[11px] font-mono bg-[#1a202c] text-[#e2e8f0] p-3 rounded-lg overflow-x-auto">
                <code>SELECT count(*) AS rows, ... FROM dataset  -- DuckDB aggregate query</code>
              </pre>
            </details>
          </div>

          {/* Correlations */}
          {data.correlations?.significant_pairs?.length > 0 && (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
              <h2 className="text-lg font-bold text-[#1a202c] mb-3">🔗 Significant Correlations (SQL CORR)</h2>
              <div className="space-y-2">
                {data.correlations.significant_pairs.slice(0, 10).map((pair: { col1: string; col2: string; correlation: string; strength: string; direction: string }, i: number) => (
                  <p key={i} className="text-sm text-[#4a5568]">
                    {pair.direction === 'positive' ? '📈' : '📉'} <strong>{pair.col1}</strong> ↔ <strong>{pair.col2}</strong>: {pair.correlation} ({pair.strength}, {pair.direction})
                  </p>
                ))}
              </div>
              {data.sql_queries?.correlations && (
                <details className="mt-2">
                  <summary className="text-xs text-[#718096] cursor-pointer hover:text-[#1a202c]">📝 View SQL</summary>
                  <pre className="mt-1 text-[11px] font-mono bg-[#1a202c] text-[#e2e8f0] p-3 rounded-lg overflow-x-auto">
                    <code>{data.sql_queries.correlations}</code>
                  </pre>
                </details>
              )}
            </div>
          )}

          {/* Outliers */}
          {data.outliers && Object.keys(data.outliers).length > 0 && (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
              <h2 className="text-lg font-bold text-[#1a202c] mb-3">⚠️ Detected Outliers</h2>
              <div className="space-y-1">
                {Object.entries(data.outliers).map(([col, info]: [string, unknown]) => {
                  const i = info as { count: number; percentage: string; lower_bound: number; upper_bound: number };
                  return (
                    <p key={col} className="text-sm text-[#4a5568]">
                      <strong>{col}</strong>: {i.count} outliers ({i.percentage}%) — outside [{i.lower_bound.toFixed(2)}, {i.upper_bound.toFixed(2)}]
                    </p>
                  );
                })}
              </div>
            </div>
          )}

          {/* Trends */}
          {data.trends.length > 0 && (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
              <h2 className="text-lg font-bold text-[#1a202c] mb-3">📈 Trends (SQL REGR_SLOPE)</h2>
              <div className="space-y-2">
                {data.trends.slice(0, 10).map((trend, i) => (
                  <p key={i} className="text-sm text-[#4a5568]">
                    {trend.trend === 'upward' ? '🟢' : '🔴'} <strong>{trend.column}</strong>: {trend.trend} (slope={trend.slope}, R²={trend.r_squared}) {trend.significant ? '✅' : ''}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* LLM Insights */}
          {data.llm_insights && !data.llm_insights.includes('Could not generate') && (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0]">
              <h2 className="text-lg font-bold text-[#1a202c] mb-3">🧠 AI-Generated Insights</h2>
              <p className="text-sm text-[#4a5568] whitespace-pre-wrap">{data.llm_insights}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

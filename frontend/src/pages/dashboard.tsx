import { useState } from 'react';
import { api } from '../lib/api';
import { InteractiveChartRenderer } from '../components/charts/interactive-chart-renderer';
import { SQLViewer } from '../components/charts/sql-viewer';
import { useDashboard } from '../context/dashboard-context';
import { X, Filter } from 'lucide-react';
import type { DatasetInfo } from '../types';

interface DashboardPageProps {
  dataset: DatasetInfo;
}

export function DashboardPage({ dataset }: DashboardPageProps) {
  const [maxCharts, setMaxCharts] = useState(6);
  const [useLlm, setUseLlm] = useState(false);
  const [charts, setCharts] = useState<{ figure: Record<string, unknown>; sql?: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'chart' | 'sql'>('chart');
  const { filters, addFilter, removeFilter, clearFilters, hasActiveFilters } = useDashboard();

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.generateDashboard({
        dataset_id: dataset.id,
        max_charts: maxCharts,
        use_llm: useLlm,
        filters: filters.map((f) => ({ column: f.column, operator: f.operator || 'in', values: f.values })),
      });
      const chartData = (res.charts || []).map((fig, i) => ({
        figure: fig,
        sql: res.sqls?.[i],
      }));
      setCharts(chartData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to generate dashboard');
    } finally {
      setLoading(false);
    }
  };

  /** Cross-filter: when user selects data in a chart, add a filter and re-generate */
  const handleSelection = (column: string, values: unknown[]) => {
    if (values.length > 0) {
      addFilter({ column, operator: 'in', values: [...new Set(values)] });
      // Re-generate charts with the new filter applied
      setTimeout(generate, 50);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">📊</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Dashboard Builder</h1>
          <p className="text-sm text-[#718096] m-0">Click any chart element to cross-filter all other charts</p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-6 items-end mb-4 p-4 rounded-xl bg-white border border-[#e8ecf0]">
        <div>
          <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Max charts</label>
          <input
            type="range"
            min={2}
            max={12}
            value={maxCharts}
            onChange={(e) => setMaxCharts(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm text-[#4a5568] ml-2">{maxCharts}</span>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#4a5568] cursor-pointer">
          <input type="checkbox" checked={useLlm} onChange={() => setUseLlm(!useLlm)} className="rounded border-[#e2e8f0]" />
          Use LLM for smart layout
        </label>
        <button
          onClick={generate}
          disabled={loading}
          className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 shadow-sm transition-all active:scale-95"
        >
          {loading ? 'Generating...' : '🚀 Generate Dashboard'}
        </button>
      </div>

      {/* Active filters bar — shows when cross-filtering is active */}
      {hasActiveFilters && (
        <div className="flex items-center gap-2 mb-4 p-3 rounded-xl bg-[#ebf4ff] border border-[#bfdbfe]">
          <Filter className="size-4 text-[#1a56db]" />
          <span className="text-xs font-semibold text-[#1a56db]">Filters:</span>
          {filters.map((f) => (
            <span key={f.column} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-white border border-[#bfdbfe] text-[#1a56db]">
              {f.column}: {String(f.values?.[0] ?? '').slice(0, 20)}
              <button onClick={() => {
                removeFilter(f.column);
                setTimeout(generate, 0);
              }} className="hover:text-[#e53e3e] ml-1">
                <X className="size-3" />
              </button>
            </span>
          ))}
          <button
            onClick={() => { clearFilters(); generate(); }}
            className="ml-auto text-xs font-medium text-[#718096] hover:text-[#e53e3e] px-2 py-1 rounded hover:bg-white transition-all"
          >
            Clear all & re-generate
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 mb-4 rounded-xl bg-[#fff5f5] border border-[#e8ecf0] text-sm text-[#e53e3e]">{error}</div>
      )}

      {charts.length === 0 && !loading && !error && (
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">
          Click "Generate Dashboard" to create visualizations — then click any chart element to cross-filter
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center h-64 text-[#718096] text-sm">
          <div className="flex gap-1.5">
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}

      {/* Global Chart/SQL toggle */}
      {charts.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <div className="flex bg-[#f7fafc] border border-[#e8ecf0] rounded-lg p-0.5">
            <button
              onClick={() => setActiveTab('chart')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'chart' ? 'bg-white text-[#1a56db] shadow-sm' : 'text-[#718096] hover:text-[#4a5568]'}`}
            >📊 Charts</button>
            <button
              onClick={() => setActiveTab('sql')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'sql' ? 'bg-white text-[#1a56db] shadow-sm' : 'text-[#718096] hover:text-[#4a5568]'}`}
            >📝 All SQL</button>
          </div>
          <span className="text-xs text-[#a0aec0]">
            {hasActiveFilters ? 'Filters active — charts filtered' : 'Click any chart bar/point to cross-filter'}
          </span>
        </div>
      )}

      {/* Chart grid with cross-filtering */}
      {activeTab === 'chart' && (
        <div className="grid grid-cols-2 gap-4">
          {charts.map((chart, i) => (
            <div key={i} className="rounded-xl bg-white border border-[#e8ecf0] overflow-hidden">
              <div className="p-2">
                <InteractiveChartRenderer
                  figure={chart.figure}
                  chartId={`chart-${i}`}
                  height={350}
                  onSelection={handleSelection}
                  enableSelection={true}
                  enableClick={false}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SQL View */}
      {activeTab === 'sql' && (
        <div className="space-y-3">
          {charts.map((chart, i) => (
            <div key={i} className="rounded-xl bg-white border border-[#e8ecf0] overflow-hidden">
              <div className="px-3 py-2 text-xs font-semibold text-[#718096] bg-[#f8f9fb] border-b border-[#e8ecf0]">
                Chart {i + 1}
              </div>
              <SQLViewer sql={chart.sql || '-- No SQL generated'} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

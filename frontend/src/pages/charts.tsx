import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { ChartWithSQL } from '../components/charts/chart-with-sql';
import type { DatasetInfo } from '../types';

interface ChartsPageProps {
  dataset: DatasetInfo | null;
}

const CHART_TYPES = [
  'bar', 'line', 'scatter', 'pie', 'area', 'histogram',
  'box', 'violin', 'heatmap', 'sunburst', 'funnel',
  'waterfall', 'treemap', 'gauge', 'sankey', 'parallel_coordinates', 'candlestick',
];

export function ChartsPage({ dataset }: ChartsPageProps) {
  const [xCol, setXCol] = useState('');
  const [yCol, setYCol] = useState('');
  const [chartType, setChartType] = useState('bar');
  const [colorCol, setColorCol] = useState('');
  const [aggregation, setAggregation] = useState('sum');
  const [figure, setFigure] = useState<Record<string, unknown> | null>(null);
  const [sql, setSql] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const columns = dataset?.columns?.map((c) => c.name) ?? [];

  const renderChart = async () => {
    if (!dataset) return;
    setLoading(true);
    try {
      // Step 1: Get the SQL via chart-data endpoint (fast, no LLM)
      const chartDataRes = await api.getChartData(dataset.id, {
        dataset_id: dataset.id,
        chart_type: chartType,
        x_column: xCol || undefined,
        y_column: yCol || undefined,
        aggregation,
        color_column: colorCol || undefined,
        limit: 5000,
      });
      setSql(chartDataRes.sql);
      console.log('[ChartBuilder] getChartData SQL:', chartDataRes.sql);

      // Step 2: Try the LLM-powered query endpoint for a full Plotly figure
      let fig: Record<string, unknown> | null = null;
      try {
        const queryRes = await api.query({
          dataset_id: dataset.id,
          question: `Show me a ${chartType} chart of ${yCol || ''} by ${xCol || ''}${colorCol ? ` colored by ${colorCol}` : ''}`,
          generate_charts: true,
        });
        console.log('[ChartBuilder] query response:', queryRes);
        if (queryRes.rendered_charts?.length > 0) {
          const maybeFig = queryRes.rendered_charts[0].figure;
          if (maybeFig && typeof maybeFig === 'object' && Object.keys(maybeFig as Record<string, unknown>).length > 0) {
            fig = maybeFig as unknown as Record<string, unknown>;
            console.log('[ChartBuilder] extracted figure from query endpoint');
          }
        }
      } catch (queryErr) {
        console.error('[ChartBuilder] query endpoint failed, falling back to direct render:', queryErr);
      }

      // Step 3: Fall back to the direct /render-chart endpoint (no LLM)
      if (!fig) {
        try {
          const directRes = await api.renderChartDirect({
            dataset_id: dataset.id,
            chart_type: chartType,
            x_column: xCol || undefined,
            y_column: yCol || undefined,
            aggregation,
            color_column: colorCol || undefined,
            limit: 5000,
          });
          console.log('[ChartBuilder] direct render response:', directRes);
          if (directRes.figure_json && Object.keys(directRes.figure_json).length > 0) {
            fig = directRes.figure_json;
            if (directRes.sql) setSql(directRes.sql);
            console.log('[ChartBuilder] extracted figure from direct render endpoint');
          }
        } catch (directErr) {
          console.error('[ChartBuilder] direct render endpoint also failed:', directErr);
        }
      }

      if (fig) {
        setFigure(fig);
      } else {
        console.error('[ChartBuilder] all render methods returned no figure');
      }
    } catch (err) {
      console.error('[ChartBuilder] renderChart error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (columns.length > 0) {
      setXCol(columns[0]);
      setYCol(columns.length > 1 ? columns[1] : columns[0]);
    }
  }, [dataset?.id]);

  if (!dataset) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🎨</span>
          <div>
            <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Chart Builder</h1>
            <p className="text-sm text-[#718096] m-0">Build custom visualizations — SQL-powered</p>
          </div>
        </div>
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">Upload data first</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">🎨</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Chart Builder</h1>
          <p className="text-sm text-[#718096] m-0">SQL-powered visualizations — 17 chart types</p>
        </div>
      </div>

      <div className="grid grid-cols-[300px_1fr] gap-6">
        {/* Controls panel */}
        <div className="space-y-4 p-5 rounded-xl bg-white border border-[#e8ecf0]">
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Chart Type</label>
            <select value={chartType} onChange={(e) => setChartType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {CHART_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">X Column</label>
            <select value={xCol} onChange={(e) => setXCol(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Y Column</label>
            <select value={yCol} onChange={(e) => setYCol(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Color (optional)</label>
            <select value={colorCol} onChange={(e) => setColorCol(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              <option value="">None</option>
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Aggregation</label>
            <select value={aggregation} onChange={(e) => setAggregation(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]">
              {['sum', 'avg', 'count', 'min', 'max', 'median', 'none'].map((a) => (
                <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
              ))}
            </select>
          </div>
          <button onClick={renderChart} disabled={loading}
            className="w-full px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 transition-all">
            {loading ? 'Rendering...' : '🎨 Render Chart'}
          </button>

          {/* SQL Preview */}
          {sql && (
            <div className="mt-2">
              <label className="text-xs font-semibold text-[#718096] uppercase block mb-1">Generated SQL</label>
              <pre className="text-[11px] font-mono bg-[#1a202c] text-[#e2e8f0] p-3 rounded-lg overflow-x-auto max-h-[200px]">
                <code>{sql}</code>
              </pre>
            </div>
          )}
        </div>

        {/* Chart preview */}
        <div className="min-h-[400px]">
          {figure ? (
            <ChartWithSQL
              figure={figure}
              sql={sql}
              title={`${chartType.replace(/_/g, ' ')} Chart`}
              height={450}
            />
          ) : (
            <div className="p-4 rounded-xl bg-white border border-[#e8ecf0] min-h-[400px] flex items-center justify-center">
              <p className="text-sm text-[#a0aec0]">Select columns and click Render Chart</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

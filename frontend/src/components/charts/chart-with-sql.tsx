/**
 * Chart + SQL Side-by-Side Viewer
 *
 * Every chart in the app gets two tabs: [📊 Chart] and [📝 SQL].
 * The SQL tab shows the actual DuckDB query that generated the chart.
 */
import { useState } from 'react';
import { ChartRenderer } from './chart-renderer';
import { SQLViewer } from './sql-viewer';

interface ChartWithSQLProps {
  figure: Record<string, unknown>;
  sql?: string | null;
  title?: string;
  height?: number;
  className?: string;
}

type Tab = 'chart' | 'sql';

export function ChartWithSQL({ figure, sql, title, height = 300, className = '' }: ChartWithSQLProps) {
  const [activeTab, setActiveTab] = useState<Tab>('chart');

  return (
    <div className={`rounded-xl bg-white border border-[#e8ecf0] overflow-hidden ${className}`}>
      {/* Tab bar */}
      <div className="flex items-center border-b border-[#e8ecf0] bg-[#f8f9fb]">
        <button
          onClick={() => setActiveTab('chart')}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'chart'
              ? 'border-[#1a56db] text-[#1a56db] bg-white'
              : 'border-transparent text-[#718096] hover:text-[#4a5568]'
          }`}
        >
          <span>📊</span>
          <span>Chart</span>
        </button>
        <button
          onClick={() => setActiveTab('sql')}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'sql'
              ? 'border-[#1a56db] text-[#1a56db] bg-white'
              : 'border-transparent text-[#718096] hover:text-[#4a5568]'
          }`}
        >
          <span>📝</span>
          <span>SQL</span>
          {sql && <span className="text-[10px] text-[#a0aec0] font-normal">({sql.length > 30 ? sql.slice(0, 30) + '…' : ''})</span>}
        </button>

        {/* Title in the right side of tab bar */}
        {title && (
          <span className="ml-auto px-4 text-xs text-[#a0aec0] truncate max-w-[200px]">
            {title}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-0">
        {activeTab === 'chart' ? (
          <div className="p-2">
            <ChartRenderer chart={{ figure }} height={height} />
          </div>
        ) : (
          <SQLViewer sql={sql || '-- No SQL generated for this chart'} />
        )}
      </div>
    </div>
  );
}

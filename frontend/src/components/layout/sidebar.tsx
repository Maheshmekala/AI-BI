import type { DatasetListItem, ModelInfo } from '../../types';
import type { useDatasets } from '../../hooks/use-datasets';
import type { useModels } from '../../hooks/use-models';
import { Zap, MessageSquare, LayoutDashboard, Lightbulb, Database, BarChart3, Settings } from 'lucide-react';

type Page = 'landing' | 'chat' | 'dashboard' | 'insights' | 'sources' | 'charts' | 'settings';

interface SidebarProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  datasets: ReturnType<typeof useDatasets>;
  models: ReturnType<typeof useModels>;
  hasData: boolean;
}

const NAV_ITEMS: { page: Page; label: string; icon: typeof MessageSquare }[] = [
  { page: 'chat', label: 'Chat & Analyze', icon: MessageSquare },
  { page: 'dashboard', label: 'Dashboard Builder', icon: LayoutDashboard },
  { page: 'insights', label: 'Auto Insights', icon: Lightbulb },
  { page: 'sources', label: 'Data Sources', icon: Database },
  { page: 'charts', label: 'Chart Builder', icon: BarChart3 },
  { page: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ currentPage, onNavigate, datasets, models, hasData }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[260px] bg-[#f8f9fb] border-r border-[#e8ecf0] flex flex-col z-50">
      {/* Logo */}
      <div className="flex items-center justify-center gap-2.5 py-5 px-4">
        <span className="text-2xl">⚡</span>
        <span className="text-xl font-bold text-[#1a202c] tracking-tight">Instant BI</span>
      </div>
      <p className="text-center text-xs text-[#a0aec0] -mt-3 mb-4">Chat with your data</p>

      <div className="border-t border-[#e8ecf0] mx-4" />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto sidebar-scroll">
        {NAV_ITEMS.map(({ page, label, icon: Icon }) => {
          const isActive = currentPage === page;
          const disabled = !hasData && (page === 'dashboard' || page === 'insights' || page === 'charts');
          return (
            <button
              key={page}
              onClick={() => !disabled && onNavigate(page)}
              disabled={disabled}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
                ${isActive
                  ? 'bg-[#ebf4ff] text-[#1a56db] border border-[#bfdbfe]'
                  : disabled
                    ? 'text-[#cbd5e0] cursor-not-allowed'
                    : 'text-[#4a5568] hover:bg-[#edf2f7] hover:text-[#1a202c] border border-transparent'
                }`}
            >
              <Icon className="size-4.5" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-[#e8ecf0] mx-4" />

      {/* Model selector */}
      <div className="px-4 py-4">
        <p className="text-xs font-semibold text-[#718096] uppercase tracking-wider mb-2">Model</p>
        {models.selectedModel ? (
          <div className="flex items-center gap-2 px-3 py-2 bg-[#ebf4ff] border border-[#bfdbfe] rounded-full text-sm text-[#1a56db] mb-2">
            <span className="size-2 rounded-full bg-[#38a169] flex-shrink-0" />
            <span className="truncate">{models.selectedModel.name}</span>
          </div>
        ) : (
          <p className="text-xs text-[#a0aec0]">No models available</p>
        )}
        {models.models.length > 0 && (
          <select
            value={models.selectedModel?.id || ''}
            onChange={(e) => {
              const m = models.models.find((m) => m.id === e.target.value);
              if (m) models.setSelectedModel(m);
            }}
            className="w-full text-xs rounded-full border border-[#e2e8f0] bg-white px-3 py-1.5 text-[#4a5568] outline-none focus:border-[#93bbfc]"
          >
            {models.models.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Active dataset info */}
      {hasData && datasets.activeDataset && (
        <div className="mx-4 mb-4 p-3 rounded-xl bg-[#ebf4ff] border border-[#bfdbfe]">
          <p className="text-[10px] font-semibold text-[#718096] uppercase tracking-wider mb-1">Active Data</p>
          <p className="text-sm font-medium text-[#1a202c] truncate">{datasets.activeDataset.name}</p>
          <p className="text-xs text-[#718096]">
            {datasets.activeDataset.row_count.toLocaleString()} rows · {datasets.activeDataset.column_count} cols
          </p>
        </div>
      )}

      <div className="mx-4 mb-2 text-[10px] text-[#a0aec0] text-center">
        {datasets.datasets.length} data source{datasets.datasets.length !== 1 ? 's' : ''}
      </div>
    </aside>
  );
}

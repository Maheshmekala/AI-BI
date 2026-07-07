import { RayBackground } from '../components/landing/ray-background';
import { Upload, Database, Zap } from 'lucide-react';
import type { useDatasets } from '../hooks/use-datasets';

type Page = 'landing' | 'chat' | 'dashboard' | 'insights' | 'sources' | 'charts' | 'settings';

interface LandingPageProps {
  onNavigate: (page: Page) => void;
  datasets: ReturnType<typeof useDatasets>;
}

export function LandingPage({ onNavigate, datasets }: LandingPageProps) {
  return (
    <div className="relative min-h-[calc(100vh-3rem)] flex flex-col items-center justify-center px-4">
      <RayBackground />

      {/* Announcement badge */}
      <a
        href="#"
        className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium text-[#1a56db] bg-[#f0f5ff] border border-[#bfdbfe] shadow-sm hover:scale-[1.02] transition-transform"
      >
        <Zap className="size-4" />
        Introducing Instant BI V2
      </a>

      {/* Title */}
      <h1 className="text-4xl sm:text-5xl font-extrabold text-[#1a202c] tracking-tight text-center mt-6 leading-tight">
        What will you{' '}
        <span className="bg-gradient-to-b from-[#3b82f6] via-[#1a56db] to-[#1a202c] bg-clip-text text-transparent italic">
          analyze
        </span>{' '}
        today?
      </h1>

      <p className="text-base sm:text-lg text-[#718096] font-medium text-center mt-3 max-w-lg">
        Upload data, connect databases, and get instant dashboards, reports & insights powered by AI.
      </p>

      {/* Quick action buttons */}
      <div className="flex gap-3 mt-8">
        <label className="cursor-pointer inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#1a56db] shadow-md hover:bg-[#1e60e0] transition-all active:scale-95">
          <Upload className="size-4" />
          Upload Data
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.pdf"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) {
                try {
                  await datasets.uploadFile(file);
                  onNavigate('chat');
                } catch {}
              }
            }}
          />
        </label>
        <button
          onClick={() => onNavigate('sources')}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium text-[#4a5568] bg-white border border-[#e2e8f0] hover:bg-[#f7fafc] hover:text-[#1a202c] transition-all active:scale-95"
        >
          <Database className="size-4" />
          Connect DB
        </button>
        <button
          onClick={() => onNavigate('chat')}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium text-[#4a5568] bg-white border border-[#e2e8f0] hover:bg-[#f7fafc] hover:text-[#1a202c] transition-all active:scale-95"
        >
          Quick Start
        </button>
      </div>

      {/* Quick-start tips */}
      <div className="flex flex-wrap gap-4 justify-center mt-10">
        {[
          { icon: '📁', label: 'Upload CSV / Excel / PDF' },
          { icon: '💬', label: 'Ask questions in plain English' },
          { icon: '📊', label: 'Auto-generated dashboards' },
        ].map((tip, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#f7fafc] border border-[#e8ecf0] text-sm text-[#4a5568]"
          >
            <span className="text-lg">{tip.icon}</span>
            <span>{tip.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

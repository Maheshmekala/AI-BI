import { useState, useRef, useEffect } from 'react';
import { SendHorizontal, Lightbulb, Code, BarChart3 } from 'lucide-react';
import type { DatasetInfo } from '../types';
import type { useChat, ChatMessage } from '../hooks/use-chat';
import type { useModels } from '../hooks/use-models';
import { ChartRenderer } from '../components/charts/chart-renderer';
import { SQLViewer } from '../components/charts/sql-viewer';

interface ChatPageProps {
  dataset: DatasetInfo;
  chat: ReturnType<typeof useChat>;
  models: ReturnType<typeof useModels>;
}

export function ChatPage({ dataset, chat, models }: ChatPageProps) {
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages]);

  const handleSend = () => {
    if (!input.trim() || chat.loading) return;
    chat.sendMessage(dataset.id, input.trim(), {
      model: models.selectedModel?.id,
      provider: models.selectedModel?.provider,
    });
    setInput('');
  };

  const isDashboardRequest = (q: string) =>
    ['dashboard', 'kpi', 'overview', 'summarize everything'].some((kw) =>
      q.toLowerCase().includes(kw)
    );

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">💬</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Chat & Analyze</h1>
          <p className="text-sm text-[#718096] m-0">Ask questions about your data in natural language</p>
        </div>
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full text-xs text-[#718096] bg-[#ebf4ff] border border-[#bfdbfe]">
          <span className="size-2 rounded-full bg-[#38a169]" />
          {dataset.name}
        </div>
      </div>

      {/* Dataset stats */}
      <div className="flex gap-4 mb-4 p-4 rounded-xl bg-white border border-[#e8ecf0]">
        <div className="text-center flex-1">
          <p className="text-[10px] font-semibold text-[#718096] uppercase">Dataset</p>
          <p className="text-lg font-bold text-[#1a202c]">{dataset.name}</p>
        </div>
        <div className="text-center flex-1 border-x border-[#e8ecf0]">
          <p className="text-[10px] font-semibold text-[#718096] uppercase">Rows</p>
          <p className="text-lg font-bold text-[#1a202c]">{dataset.row_count.toLocaleString()}</p>
        </div>
        <div className="text-center flex-1">
          <p className="text-[10px] font-semibold text-[#718096] uppercase">Columns</p>
          <p className="text-lg font-bold text-[#1a202c]">{dataset.column_count}</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 px-1">
        {chat.messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-[#a0aec0] text-sm">
            Ask a question about your data to get started
          </div>
        )}

        {chat.messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl p-4 ${
                msg.role === 'user'
                  ? 'bg-[#ebf4ff] border border-[#bfdbfe]'
                  : 'bg-[#f7fafc] border border-[#e8ecf0]'
              }`}
            >
              <p className="text-sm text-[#2d3748] whitespace-pre-wrap leading-relaxed">{msg.content}</p>

              {/* Charts — each with Chart/SQL/Data tabs */}
              {msg.charts && msg.charts.length > 0 && (
                <div className="mt-3 space-y-4">
                  {msg.charts.map((chart, ci) => (
                    <ChartTabCard key={ci} chart={chart} sql={msg.sql || chart.sql || ''} index={ci} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {chat.loading && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl p-4 bg-[#f7fafc] border border-[#e8ecf0]">
              <div className="flex gap-1.5">
                <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="size-2 rounded-full bg-[#3b82f6] animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Chat input */}
      <div className="relative">
        <div className="rounded-2xl bg-white border border-[#e2e8f0] shadow-sm focus-within:border-[#3b82f6] focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.12)] transition-all">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask a question about your data..."
            rows={2}
            className="w-full resize-none bg-transparent text-sm text-[#1a202c] placeholder-[#a0aec0] px-5 pt-4 pb-2 outline-none"
            style={{ minHeight: '64px' }}
          />
          <div className="flex items-center justify-between px-3 pb-3 pt-1">
            <div className="flex items-center gap-1">
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-[#718096] hover:text-[#1a202c] hover:bg-[#f7fafc] transition-all">
                <Lightbulb className="size-4" />
                <span className="hidden sm:inline">Plan</span>
              </button>
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || chat.loading}
              className="flex items-center gap-2 px-5 py-2 rounded-full text-sm font-semibold bg-[#1a56db] text-white transition-all hover:bg-[#1e60e0] disabled:opacity-40 disabled:cursor-not-allowed active:scale-95 shadow-sm"
            >
              <span className="hidden sm:inline">Send</span>
              <SendHorizontal className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Chart tab card — shows Chart / SQL tabs for a single chart.
 */
function ChartTabCard({ chart, sql, index }: { chart: any; sql: string; index: number }) {
  const [activeTab, setActiveTab] = useState<'chart' | 'sql'>('chart');

  return (
    <div className="rounded-xl bg-white border border-[#e8ecf0] overflow-hidden">
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
          <BarChart3 className="size-3.5" />
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
          <Code className="size-3.5" />
          <span>SQL</span>
        </button>
        {chart.title && (
          <span className="ml-auto px-4 text-xs text-[#a0aec0] truncate max-w-[160px]">
            {chart.title}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-0">
        {activeTab === 'chart' && (
          <div className="p-2">
            <ChartRenderer chart={chart} height={280} />
          </div>
        )}
        {activeTab === 'sql' && (
          <SQLViewer sql={sql || '-- No SQL generated'} maxHeight={250} />
        )}
      </div>
    </div>
  );
}

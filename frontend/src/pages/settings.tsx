import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { SettingsInfo } from '../types';

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSettings().then(setSettings).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">⚙️</span>
          <div>
            <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Settings</h1>
            <p className="text-sm text-[#718096] m-0">Configure application behavior</p>
          </div>
        </div>
        <div className="flex items-center justify-center h-64 text-[#a0aec0] text-sm">Loading...</div>
      </div>
    );
  }

  if (!settings) return null;

  const providers: { name: string; key: string; configured: boolean }[] = [
    { name: 'Groq', key: settings.groq_api_key, configured: !!settings.groq_api_key },
    { name: 'OpenAI', key: settings.openai_api_key, configured: !!settings.openai_api_key },
    { name: 'Anthropic', key: settings.anthropic_api_key, configured: !!settings.anthropic_api_key },
    { name: 'Google', key: settings.google_api_key, configured: !!settings.google_api_key },
    { name: 'Ollama (Local)', key: '', configured: true },
  ];

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">⚙️</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Settings</h1>
          <p className="text-sm text-[#718096] m-0">Configure application behavior</p>
        </div>
      </div>

      {/* Provider Status */}
      <div className="p-5 rounded-xl bg-white border border-[#e8ecf0] mb-4">
        <h2 className="text-lg font-bold text-[#1a202c] mb-3">🤖 LLM Configuration</h2>
        <p className="text-xs text-[#718096] mb-4">Configure your LLM providers via the `.env` file or environment variables.</p>
        <h3 className="text-sm font-semibold text-[#4a5568] mb-3">Provider Status</h3>
        <div className="grid grid-cols-5 gap-3">
          {providers.map((p) => (
            <div key={p.name} className="text-center p-3 rounded-xl bg-[#f7fafc] border border-[#e8ecf0]">
              <p className={`text-xs font-semibold ${p.configured ? 'text-[#38a169]' : 'text-[#e53e3e]'}`}>
                {p.configured ? '✅ Configured' : '❌ Not set'}
              </p>
              <p className="text-sm text-[#4a5568] mt-1">{p.name}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Data Configuration */}
      <div className="p-5 rounded-xl bg-white border border-[#e8ecf0] mb-4">
        <h2 className="text-lg font-bold text-[#1a202c] mb-3">📁 Data Configuration</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 rounded-xl bg-[#f7fafc] border border-[#e8ecf0]">
            <p className="text-[10px] font-semibold text-[#718096] uppercase">Upload Directory</p>
            <p className="text-sm text-[#4a5568] mt-1">uploads/</p>
          </div>
          <div className="text-center p-3 rounded-xl bg-[#f7fafc] border border-[#e8ecf0]">
            <p className="text-[10px] font-semibold text-[#718096] uppercase">Cache TTL</p>
            <p className="text-sm text-[#4a5568] mt-1">{settings.cache_ttl_seconds}s</p>
          </div>
        </div>
      </div>

      {/* Session Info */}
      <div className="p-5 rounded-xl bg-white border border-[#e8ecf0]">
        <h2 className="text-lg font-bold text-[#1a202c] mb-3">ℹ️ Session Info</h2>
        <pre className="text-xs text-[#718096] bg-[#f7fafc] p-3 rounded-xl border border-[#e8ecf0] overflow-auto">
          {JSON.stringify({
            app_name: settings.app_name,
            debug: settings.debug,
            available_providers: settings.available_providers,
            max_upload_size_mb: settings.max_upload_size_mb,
          }, null, 2)}
        </pre>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { api } from '../lib/api';
import type { DatasetInfo, DatasetListItem } from '../types';

interface SourcesPageProps {
  datasets: {
    datasets: DatasetListItem[];
    activeDataset: DatasetInfo | null;
    uploadFile: (file: File) => Promise<unknown>;
    connectDb: (config: unknown) => Promise<unknown>;
    selectDataset: (id: string) => Promise<void>;
    removeDataset: (id: string) => Promise<void>;
    loading: boolean;
    error: string | null;
  };
}

type DbType = 'PostgreSQL' | 'MySQL' | 'SQLite' | 'Other';

export function SourcesPage({ datasets }: SourcesPageProps) {
  const [tab, setTab] = useState<'upload' | 'database' | 'manage'>('upload');

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">🗄️</span>
        <div>
          <h1 className="text-2xl font-extrabold text-[#1a202c] m-0">Data Sources</h1>
          <p className="text-sm text-[#718096] m-0">Upload files or connect to databases</p>
        </div>
      </div>

      <div className="flex gap-1 mb-6 p-1 rounded-xl bg-[#f7fafc] border border-[#e8ecf0] w-fit">
        {(['upload', 'database', 'manage'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t ? 'bg-white text-[#1a56db] shadow-sm' : 'text-[#718096] hover:text-[#4a5568]'
            }`}
          >
            {t === 'upload' ? '📁 Upload File' : t === 'database' ? '🔌 Database' : '📋 Manage Sources'}
          </button>
        ))}
      </div>

      {tab === 'upload' && <UploadTab datasets={datasets} />}
      {tab === 'database' && <DatabaseTab datasets={datasets} />}
      {tab === 'manage' && <ManageTab datasets={datasets} />}
    </div>
  );
}

function UploadTab({ datasets }: { datasets: SourcesPageProps['datasets'] }) {
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    try {
      const result = await datasets.uploadFile(file);
      alert(result.message || 'Upload successful');
    } catch {
      // error is handled by hook
    }
  };

  return (
    <div className="p-6 rounded-xl bg-white border border-[#e8ecf0]">
      <div
        className="border-2 border-dashed border-[#e2e8f0] rounded-2xl p-10 text-center hover:border-[#3b82f6] hover:bg-[#ebf4ff] transition-all cursor-pointer"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          id="file-upload"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <p className="text-3xl mb-2">📁</p>
          <p className="text-sm font-medium text-[#4a5568]">Click to upload or drag and drop</p>
          <p className="text-xs text-[#a0aec0] mt-1">CSV, Excel (.xlsx/.xls), or PDF</p>
        </label>
      </div>

      {file && (
        <div className="mt-4 flex items-center justify-between p-3 rounded-xl bg-[#f7fafc] border border-[#e8ecf0]">
          <div>
            <p className="text-sm font-medium text-[#1a202c]">{file.name}</p>
            <p className="text-xs text-[#718096]">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <button
            onClick={handleUpload}
            disabled={datasets.loading}
            className="px-5 py-2 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 transition-all"
          >
            {datasets.loading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      )}

      {datasets.error && (
        <p className="mt-3 text-sm text-[#e53e3e]">{datasets.error}</p>
      )}
    </div>
  );
}

function DatabaseTab({ datasets }: { datasets: SourcesPageProps['datasets'] }) {
  const [dbType, setDbType] = useState<DbType>('PostgreSQL');
  const [host, setHost] = useState('localhost');
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState('');
  const [user, setUser] = useState('postgres');
  const [password, setPassword] = useState('');
  const [connName, setConnName] = useState('My DB');
  const [connString, setConnString] = useState('');

  const handleConnect = async () => {
    const config: Record<string, unknown> = { db_type: dbType, connection_name: connName };
    if (dbType === 'SQLite') {
      config.database = database;
    } else if (dbType === 'Other') {
      config.connection_string = connString;
    } else {
      config.host = host;
      config.port = port;
      config.database = database;
      config.user = user;
      config.password = password;
    }
    try {
      const result = await datasets.connectDb(config);
      alert(result.message || 'Connected!');
    } catch {
      // error handled by hook
    }
  };

  return (
    <div className="p-6 rounded-xl bg-white border border-[#e8ecf0]">
      <select
        value={dbType}
        onChange={(e) => {
          const t = e.target.value as DbType;
          setDbType(t);
          if (t === 'MySQL') setPort(3306);
          else if (t === 'PostgreSQL') setPort(5432);
        }}
        className="w-full mb-4 px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm text-[#1a202c] outline-none focus:border-[#3b82f6]"
      >
        <option>PostgreSQL</option>
        <option>MySQL</option>
        <option>SQLite</option>
        <option>Other (SQLAlchemy URL)</option>
      </select>

      {dbType === 'SQLite' ? (
        <input
          placeholder="SQLite File Path (e.g., data.db)"
          value={database}
          onChange={(e) => setDatabase(e.target.value)}
          className="w-full mb-3 px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]"
        />
      ) : dbType === 'Other' ? (
        <input
          placeholder="postgresql://user:pass@host:5432/db"
          value={connString}
          onChange={(e) => setConnString(e.target.value)}
          className="w-full mb-3 px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]"
        />
      ) : (
        <div className="grid grid-cols-2 gap-3 mb-3">
          <input placeholder="Host" value={host} onChange={(e) => setHost(e.target.value)} className="px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]" />
          <input type="number" placeholder="Port" value={port} onChange={(e) => setPort(Number(e.target.value))} className="px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]" />
          <input placeholder="Database" value={database} onChange={(e) => setDatabase(e.target.value)} className="px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]" />
          <input placeholder="Username" value={user} onChange={(e) => setUser(e.target.value)} className="px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]" />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]" />
        </div>
      )}

      <input
        placeholder="Connection Name"
        value={connName}
        onChange={(e) => setConnName(e.target.value)}
        className="w-full mb-4 px-4 py-2.5 rounded-xl border border-[#e2e8f0] text-sm outline-none focus:border-[#3b82f6]"
      />

      <button
        onClick={handleConnect}
        disabled={datasets.loading}
        className="w-full px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#1a56db] hover:bg-[#1e60e0] disabled:opacity-40 transition-all"
      >
        {datasets.loading ? 'Connecting...' : '🔌 Connect'}
      </button>

      {datasets.error && <p className="mt-3 text-sm text-[#e53e3e]">{datasets.error}</p>}
    </div>
  );
}

function ManageTab({ datasets }: { datasets: SourcesPageProps['datasets'] }) {
  return (
    <div className="space-y-3">
      {datasets.datasets.length === 0 ? (
        <div className="p-6 rounded-xl bg-white border border-[#e8ecf0] text-center text-sm text-[#a0aec0]">
          No data sources registered yet.
        </div>
      ) : (
        datasets.datasets.map((ds) => (
          <div key={ds.id} className="flex items-center justify-between p-4 rounded-xl bg-white border border-[#e8ecf0]">
            <div>
              <p className="text-sm font-medium text-[#1a202c]">{ds.name}</p>
              <p className="text-xs text-[#718096]">{ds.row_count.toLocaleString()} rows · {ds.column_count} cols · {ds.source_type}</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => datasets.selectDataset(ds.id)}
                className="px-4 py-1.5 rounded-lg text-xs font-medium text-[#1a56db] bg-[#ebf4ff] border border-[#bfdbfe] hover:bg-[#dbeafe]"
              >
                Load
              </button>
              <button
                onClick={() => datasets.removeDataset(ds.id)}
                className="px-4 py-1.5 rounded-lg text-xs font-medium text-[#e53e3e] bg-[#fff5f5] border border-[#fed7d7] hover:bg-[#fed7d7]"
              >
                Remove
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

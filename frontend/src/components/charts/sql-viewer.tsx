/**
 * SQL Viewer — syntax-highlighted SQL display with copy button.
 *
 * Shows the exact DuckDB SQL query that was executed to generate a chart.
 * Dark terminal-style background with vibrant syntax highlighting.
 */
import { useState, useCallback } from 'react';
import { Copy, Check, Play } from 'lucide-react';

interface SQLViewerProps {
  sql: string;
  onRunAsQuery?: (sql: string) => void;
  maxHeight?: number;
}

export function SQLViewer({ sql, onRunAsQuery, maxHeight = 400 }: SQLViewerProps) {
  // Ensure sql is always a string — fix all contamination
  const sqlStr = (() => {
    if (typeof sql === 'string') return sql;
    if (sql === null || sql === undefined) return '';
    if (Array.isArray(sql)) return sql.filter(Boolean).join('\n');
    try { return String(sql); } catch { return ''; }
  })().replace(/\[object Object\]/gi, '').replace(/\[object\s+\w*\]/gi, '').trim();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(sqlStr);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = sqlStr;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [sql]);

  return (
    <div className="relative" style={{ maxHeight }}>
      {/* Action buttons */}
      <div className="absolute top-2 right-2 flex items-center gap-1.5 z-10">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium bg-[#2d3748] border border-[#4a5568] text-[#a0aec0] hover:text-white hover:bg-[#4a5568] transition-all"
          title="Copy SQL"
        >
          {copied ? <Check className="size-3.5 text-[#38a169]" /> : <Copy className="size-3.5" />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
        {onRunAsQuery && (
          <button
            onClick={() => onRunAsQuery(sql)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium bg-[#1a365d] border border-[#2b6cb0] text-[#90cdf4] hover:bg-[#2b6cb0] transition-all"
            title="Run as new query"
          >
            <Play className="size-3.5" />
            <span>Run</span>
          </button>
        )}
      </div>

      {/* SQL content with vibrant syntax highlighting — terminal style */}
      <pre className="text-sm font-mono leading-relaxed overflow-x-auto p-4 pt-12 m-0 bg-[#0d1117] text-[#e2e8f0] rounded-lg border border-[#1f2937]">
        <code>{highlightSQL(sqlStr)}</code>
      </pre>
    </div>
  );
}

/**
 * Vibrant SQL syntax highlighting — converts SQL text to colored spans.
 * Terminal-inspired theme with high-contrast colors on dark background.
 */
function highlightSQL(sql: string): React.ReactNode {
  if (!sql) return null;

  // Nuke [object Object] contamination before highlighting
  const clean = sql.replace(/\[object Object\]/gi, '').replace(/\[object\s+\w*\]/gi, '').trim();
  if (!clean) return <span className="text-[#6b7280] italic">-- No SQL generated</span>;

  // SQL keywords — bright blue/purple
  const keywords = new Set([
    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'AS', 'ON',
    'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'CROSS', 'FULL',
    'GROUP', 'BY', 'ORDER', 'ASC', 'DESC', 'HAVING', 'LIMIT', 'OFFSET',
    'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE',
    'TABLE', 'VIEW', 'DROP', 'ALTER', 'INDEX', 'DISTINCT', 'ALL',
    'UNION', 'EXCEPT', 'INTERSECT', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'WITH', 'RECURSIVE', 'ROW_NUMBER', 'RANK', 'DENSE_RANK',
    'OVER', 'PARTITION', 'LAG', 'LEAD', 'FIRST', 'LAST', 'DATE_TRUNC',
    'EXTRACT', 'DATE_PART', 'DATEDIFF', 'DATEADD', 'YEAR', 'MONTH', 'DAY',
    'QUARTER', 'WEEK', 'WEEKDAY', 'PERCENTILE_CONT', 'REGR_SLOPE', 'REGR_R2',
    'WIDTH_BUCKET', 'ATTACH', 'DETACH', 'TYPE', 'IF', 'REPLACE',
  ]);

  // Aggregate functions — bright cyan
  const aggregates = new Set([
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'MEDIAN', 'CORR', 'STDDEV',
    'VAR', 'COALESCE', 'NULLIF', 'CAST',
  ]);

  // Boolean/nulls — bright green
  const literals = new Set([
    'TRUE', 'FALSE', 'NULL',
  ]);

  // Comparison — bright yellow
  const comparisons = new Set([
    'LIKE', 'BETWEEN', 'IS', 'ILIKE',
  ]);

  // Split into tokens and rebuild with spans
  const tokens = clean.split(/(\b\w+\b|'[^']*'|"[^"]*"|\s+|--[^\n]*)/g);

  return tokens.map((token, i) => {
    const upper = token.toUpperCase();
    if (keywords.has(upper)) {
      return <span key={i} className="text-[#7dd3fc] font-semibold">{token}</span>;
    }
    if (aggregates.has(upper)) {
      return <span key={i} className="text-[#22d3ee] font-semibold">{token}</span>;
    }
    if (literals.has(upper)) {
      return <span key={i} className="text-[#4ade80] font-semibold">{token}</span>;
    }
    if (comparisons.has(upper)) {
      return <span key={i} className="text-[#facc15] font-semibold">{token}</span>;
    }
    if (token.startsWith("'") || token.startsWith('"')) {
      // String literals — bright green
      return <span key={i} className="text-[#a3e635]">{token}</span>;
    }
    if (/^\d+(\.\d+)?$/.test(token.trim())) {
      // Numbers — orange
      return <span key={i} className="text-[#fb923c]">{token}</span>;
    }
    if (token.startsWith('--')) {
      // Comments — muted gray italic
      return <span key={i} className="text-[#6b7280] italic">{token}</span>;
    }
    if (token.trim() === '') {
      return token; // Whitespace — no wrapper
    }
    // Regular identifiers — light gray
    return <span key={i} className="text-[#e2e8f0]">{token}</span>;
  });
}

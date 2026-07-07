/**
 * Hook — tracks generated SQL alongside chart data.
 *
 * Every chart that renders via the backend returns its SQL query.
 * This hook stores the SQL so the Chart+SQL viewer can display it.
 */
import { useState, useCallback } from 'react';

export interface ChartSqlPair {
  chartId: string;
  sql: string;
  title: string;
}

export function useChartSql() {
  const [chartSqls, setChartSqls] = useState<ChartSqlPair[]>([]);

  const addSql = useCallback((chartId: string, sql: string, title: string = '') => {
    setChartSqls((prev) => {
      const existing = prev.findIndex((p) => p.chartId === chartId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { chartId, sql, title };
        return updated;
      }
      return [...prev, { chartId, sql, title }];
    });
  }, []);

  const getSql = useCallback((chartId: string): string | null => {
    const pair = chartSqls.find((p) => p.chartId === chartId);
    return pair?.sql ?? null;
  }, [chartSqls]);

  const clearSqls = useCallback(() => {
    setChartSqls([]);
  }, []);

  const allSql = useCallback((): ChartSqlPair[] => {
    return [...chartSqls];
  }, [chartSqls]);

  return { chartSqls, addSql, getSql, clearSqls, allSql };
}

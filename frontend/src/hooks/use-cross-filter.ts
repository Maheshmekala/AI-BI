/**
 * Cross-Filter Hook — manages cross-filtering state between charts.
 *
 * When a user selects points in one chart, this hook computes
 * the resulting filter state and provides the filtered data.
 *
 * The filters are sent to the backend as SQL WHERE clauses,
 * so only aggregated results are returned — not filtered datasets.
 */
import { useState, useCallback, useMemo } from 'react';
import type { FilterSpec } from '../context/dashboard-context';

interface CrossFilterState {
  filters: FilterSpec[];
  activeColumns: string[];
  hasActiveFilters: boolean;
}

export function useCrossFilter() {
  const [filters, setFilters] = useState<FilterSpec[]>([]);

  /** Apply or toggle a filter */
  const applyFilter = useCallback((column: string, values: unknown[]) => {
    if (!values.length) return;

    setFilters((prev) => {
      const existing = prev.findIndex((f) => f.column === column);
      const newFilter: FilterSpec = {
        column,
        operator: 'in',
        values,
      };

      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = newFilter;
        return updated;
      }
      return [...prev, newFilter];
    });
  }, []);

  /** Remove a filter by column name */
  const removeFilter = useCallback((column: string) => {
    setFilters((prev) => prev.filter((f) => f.column !== column));
  }, []);

  /** Clear all filters */
  const clearFilters = useCallback(() => {
    setFilters([]);
  }, []);

  /** Get the filter spec for a specific column */
  const getFilter = useCallback((column: string): FilterSpec | undefined => {
    return filters.find((f) => f.column === column);
  }, [filters]);

  const activeColumns = useMemo(() => {
    return filters.map((f) => f.column);
  }, [filters]);

  const hasActiveFilters = filters.length > 0;

  const state: CrossFilterState = useMemo(() => ({
    filters,
    activeColumns,
    hasActiveFilters,
  }), [filters, activeColumns, hasActiveFilters]);

  return {
    ...state,
    applyFilter,
    removeFilter,
    clearFilters,
    getFilter,
  };
}

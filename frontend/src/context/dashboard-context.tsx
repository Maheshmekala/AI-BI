/**
 * Dashboard Context — shared state for cross-filtering and parameters.
 *
 * Manages:
 * - Filter state: which values are selected in which columns
 * - Filtered dataset: computed intersection of all active filters
 * - Drill-down state: current hierarchy level
 * - Parameter values: what-if analysis controls
 */
import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

// ── Types ──

export interface FilterSpec {
  column: string;
  operator: 'in' | 'not_in' | 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'contains';
  value?: unknown;
  values?: unknown[];
}

export interface ParameterSpec {
  name: string;
  type: 'number' | 'string' | 'date' | 'list';
  currentValue: unknown;
  defaultValue: unknown;
  minValue?: number;
  maxValue?: number;
  validValues?: unknown[];
  step?: number;
}

export interface DrillState {
  hierarchyName: string | null;
  currentLevel: number;
  breadcrumbs: { level: number; label: string; value: unknown }[];
}

// ── Context ──

interface DashboardContextType {
  // Filters
  filters: FilterSpec[];
  addFilter: (filter: FilterSpec) => void;
  removeFilter: (column: string) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;

  // Parameters
  parameters: ParameterSpec[];
  setParameterValue: (name: string, value: unknown) => void;
  addParameter: (param: ParameterSpec) => void;
  removeParameter: (name: string) => void;

  // Drill-down
  drill: DrillState;
  drillDown: (hierarchyName: string, level: number, label: string, value: unknown) => void;
  drillUp: () => void;
  clearDrill: () => void;

  // Active dataset
  activeDatasetId: string | null;
  setActiveDatasetId: (id: string | null) => void;
}

const defaultDrillState: DrillState = {
  hierarchyName: null,
  currentLevel: 0,
  breadcrumbs: [],
};

const DashboardContext = createContext<DashboardContextType | null>(null);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<FilterSpec[]>([]);
  const [parameters, setParameters] = useState<ParameterSpec[]>([]);
  const [drill, setDrill] = useState<DrillState>(defaultDrillState);
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);

  // ── Filter actions ──
  const addFilter = useCallback((filter: FilterSpec) => {
    setFilters((prev) => {
      const existing = prev.findIndex((f) => f.column === filter.column);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = filter;
        return updated;
      }
      return [...prev, filter];
    });
  }, []);

  const removeFilter = useCallback((column: string) => {
    setFilters((prev) => prev.filter((f) => f.column !== column));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters([]);
  }, []);

  const hasActiveFilters = filters.length > 0;

  // ── Parameter actions ──
  const setParameterValue = useCallback((name: string, value: unknown) => {
    setParameters((prev) => {
      const existing = prev.findIndex((p) => p.name === name);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { ...updated[existing], currentValue: value };
        return updated;
      }
      return prev;
    });
  }, []);

  const addParameter = useCallback((param: ParameterSpec) => {
    setParameters((prev) => {
      const existing = prev.findIndex((p) => p.name === param.name);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = param;
        return updated;
      }
      return [...prev, param];
    });
  }, []);

  const removeParameter = useCallback((name: string) => {
    setParameters((prev) => prev.filter((p) => p.name !== name));
  }, []);

  // ── Drill actions ──
  const drillDown = useCallback((hierarchyName: string, level: number, label: string, value: unknown) => {
    setDrill((prev) => ({
      hierarchyName,
      currentLevel: level,
      breadcrumbs: [...prev.breadcrumbs, { level, label, value }],
    }));
  }, []);

  const drillUp = useCallback(() => {
    setDrill((prev) => {
      if (prev.breadcrumbs.length <= 1) {
        return defaultDrillState;
      }
      const crumbs = prev.breadcrumbs.slice(0, -1);
      return {
        hierarchyName: prev.hierarchyName,
        currentLevel: crumbs[crumbs.length - 1].level,
        breadcrumbs: crumbs,
      };
    });
  }, []);

  const clearDrill = useCallback(() => {
    setDrill(defaultDrillState);
  }, []);

  const value = useMemo(() => ({
    filters,
    addFilter,
    removeFilter,
    clearFilters,
    hasActiveFilters,
    parameters,
    setParameterValue,
    addParameter,
    removeParameter,
    drill,
    drillDown,
    drillUp,
    clearDrill,
    activeDatasetId,
    setActiveDatasetId,
  }), [
    filters, addFilter, removeFilter, clearFilters, hasActiveFilters,
    parameters, setParameterValue, addParameter, removeParameter,
    drill, drillDown, drillUp, clearDrill,
    activeDatasetId, setActiveDatasetId,
  ]);

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardContextType {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return ctx;
}

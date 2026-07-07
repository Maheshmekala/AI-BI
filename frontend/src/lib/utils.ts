import type { DatasetInfo, PlotlyFigure } from '../types';

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function getPreviewColumns(dataset: DatasetInfo): string[] {
  return dataset.columns?.map((c) => c.name) ?? [];
}

export function isPlotlyFigure(fig: unknown): fig is PlotlyFigure {
  return (
    typeof fig === 'object' &&
    fig !== null &&
    'data' in fig &&
    'layout' in fig
  );
}

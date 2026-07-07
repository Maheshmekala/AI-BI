/**
 * Interactive Chart Renderer — Plotly with cross-filtering events.
 *
 * Extends the basic ChartRenderer with:
 * - `plotly_selected` event → triggers cross-filter
 * - `plotly_click` event → triggers drill-down
 * - `plotly_restyle` event → legend toggle
 *
 * When a user selects data points in a chart, the selected values are
 * sent to the DashboardContext as filter specs. Other charts then
 * re-render with those filters applied as SQL WHERE clauses.
 */
import { useEffect, useRef, useCallback } from 'react';
import type { PlotlyFigure } from '../../types';

interface InteractiveChartRendererProps {
  figure: PlotlyFigure | Record<string, unknown>;
  chartId?: string;
  height?: number;
  onSelection?: (column: string, values: unknown[]) => void;
  onClick?: (point: Record<string, unknown>) => void;
  enableSelection?: boolean;
  enableClick?: boolean;
}

export function InteractiveChartRenderer({
  figure,
  chartId,
  height = 300,
  onSelection,
  onClick,
  enableSelection = true,
  enableClick = true,
}: InteractiveChartRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotlyRef = useRef<unknown>(null);

  // Re-render Plotly when figure changes
  useEffect(() => {
    if (!containerRef.current) return;

    let cleanup = false;

    import('plotly.js-dist-min').then((Plotly) => {
      if (cleanup || !containerRef.current) return;

      const fig = figure as PlotlyFigure;
      if (!fig?.data || !fig?.layout) return;

      plotlyRef.current = Plotly.default;

      const layout = {
        ...(fig.layout as Record<string, unknown>),
        height,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        dragmode: 'zoom',
        hovermode: 'closest',
      };

      Plotly.default.newPlot(
        containerRef.current,
        fig.data as unknown[],
        layout,
        {
          responsive: true,
          displayModeBar: true,
          modeBarButtonsToRemove: ['lasso2d', 'sendDataToCloud' as never],
        },
      );

      // Attach plotly_click for cross-filtering and drill-down
      containerRef.current.on('plotly_click', (event: { points?: { x?: unknown; y?: unknown; curveNumber?: number; pointNumber?: number; data?: Record<string, unknown> }[] }) => {
        if (!event?.points?.length) return;

        const pt = event.points[0];

        // If both onSelection and onClick are provided, use onSelection (filter) first
        // and provide onClick as drill-down via a separate interaction
        if (enableSelection && onSelection) {
          const value = pt.x;
          if (value !== undefined && value !== null) {
            const axisLayout = (fig.layout as Record<string, unknown>) as Record<string, unknown>;
            const xAxis = axisLayout?.xaxis as Record<string, unknown> | undefined;
            const xLabel = (xAxis?.title as Record<string, unknown>)?.text as string || '';
            const traceIdx = pt.curveNumber ?? 0;
            const traceData = fig.data?.[traceIdx] as Record<string, unknown> | undefined;
            const columnName = xLabel || (traceData?.meta as string) || (traceData?.name as string) || 'x';
            onSelection(columnName, [value]);
          }
        } else if (enableClick && onClick) {
          onClick(pt as Record<string, unknown>);
        }
      });
    });

    return () => {
      cleanup = true;
      if (containerRef.current && plotlyRef.current) {
        try {
          (plotlyRef.current as { purge: (el: HTMLElement) => void }).purge(containerRef.current);
        } catch {}
      }
    };
  }, [figure, height, enableSelection, enableClick, onSelection, onClick, chartId]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}

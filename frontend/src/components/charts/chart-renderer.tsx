import { useEffect, useRef } from 'react';
import type { RenderedChart, PlotlyFigure } from '../../types';

interface ChartRendererProps {
  chart: RenderedChart | { figure: Record<string, unknown> };
  height?: number;
}

export function ChartRenderer({ chart, height = 300 }: ChartRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const fig = 'figure' in chart ? chart.figure : null;
    if (!fig || !('layout' in fig)) return;

    // Load Plotly dynamically
    import('plotly.js-dist-min').then((Plotly) => {
      if (!containerRef.current) return;
      const layout = { ...fig.layout, height, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' };
      Plotly.default.newPlot(containerRef.current, fig.data as unknown as Partial<PlotlyFigure['data']>, layout, {
        responsive: true,
        displayModeBar: false,
      });
    });

    return () => {
      if (containerRef.current) {
        import('plotly.js-dist-min').then((Plotly) => {
          Plotly.default.purge(containerRef.current);
        });
      }
    };
  }, [chart, height]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}

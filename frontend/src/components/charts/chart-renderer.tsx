import { useEffect, useRef, useState } from 'react';
import type { RenderedChart, PlotlyFigure } from '../../types';

interface ChartRendererProps {
  chart: RenderedChart | { figure: Record<string, unknown> };
  height?: number;
}

export function ChartRenderer({ chart, height = 300 }: ChartRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    if (!containerRef.current) return;
    const fig = 'figure' in chart ? chart.figure : null;
    if (!fig || !fig.layout) return;

    // Load Plotly dynamically
    import('plotly.js-dist-min').then((Plotly) => {
      if (!containerRef.current) return;
      const layout = { ...fig.layout, height, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' };
      const data = Array.isArray(fig.data) ? fig.data : [];
      Plotly.default.newPlot(containerRef.current, data as unknown as Partial<PlotlyFigure['data']>, layout, {
        responsive: true,
        displayModeBar: false,
      });
    }).catch((err) => {
      console.error('Plotly import failed:', err);
      setError('Chart library failed to load');
    });

    return () => {
      if (containerRef.current) {
        import('plotly.js-dist-min').then((Plotly) => {
          Plotly.default.purge(containerRef.current);
        }).catch(() => {});
      }
    };
  }, [chart, height]);

  return (
    <>
      {error && (
        <div className="flex items-center justify-center h-full text-red-500 text-sm bg-red-50 rounded-lg p-4">
          {error}
        </div>
      )}
      <div ref={containerRef} className="w-full" style={{ height }} />
    </>
  );
}

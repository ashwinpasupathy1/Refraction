import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:7331';

interface ChartProps {
  chartType: string;
  kw: Record<string, unknown>;
  onEvent?: (event: string, value: unknown, extra: Record<string, unknown>) => void;
}

export function PlotterChart({ chartType, kw, onEvent }: ChartProps) {
  const divRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!divRef.current) return;

    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chart_type: chartType, kw }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.ok) {
          setError(data.error ?? 'Unknown error');
          return;
        }
        const spec = data.spec;
        Plotly.newPlot(divRef.current!, spec.data, spec.layout, {
          responsive: true,
          displayModeBar: true,
          editable: true,
        });

        // Wire edit events back to Python
        const div = divRef.current as unknown as Plotly.PlotlyHTMLElement;
        div.on('plotly_relayout', (update: Record<string, unknown>) => {
          if (update['title.text'] !== undefined)
            postEvent('title_changed', update['title.text']);
          if (update['xaxis.title.text'] !== undefined)
            postEvent('xlabel_changed', update['xaxis.title.text']);
          if (update['yaxis.title.text'] !== undefined)
            postEvent('ytitle_changed', update['yaxis.title.text']);
        });
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    function postEvent(
      event: string,
      value: unknown,
      extra: Record<string, unknown> = {}
    ) {
      fetch(`${API_BASE}/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, value, extra }),
      }).catch(console.error);
      onEvent?.(event, value, extra);
    }
  }, [chartType, JSON.stringify(kw)]);

  if (loading) return <div style={{ padding: 20 }}>Loading chart...</div>;
  if (error) return <div style={{ padding: 20, color: 'red' }}>Error: {error}</div>;
  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />;
}

import { useEffect, useState, useCallback } from 'react';
import './App.css';
import { PlotterChart } from './PlotterChart';
import { Sidebar } from './Sidebar';
import { ConfigPanel } from './ConfigPanel';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:7331';

interface ChartTypesResponse {
  priority: string[];
  all: string[];
}

const DEFAULT_KW: Record<string, unknown> = {
  excel_path: '',
  sheet: 0,
  title: '',
  xlabel: '',
  ytitle: '',
  color: '#2274A5',
  font_size: 12,
};

export default function App() {
  const [chartTypes, setChartTypes] = useState<string[]>([]);
  const [activeType, setActiveType] = useState('bar');
  // pendingKw: live form state; renderKw: committed on "Generate"
  const [pendingKw, setPendingKw] = useState<Record<string, unknown>>(DEFAULT_KW);
  const [renderKw, setRenderKw] = useState<Record<string, unknown> | null>(null);
  const [configCollapsed, setConfigCollapsed] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);

  // Fetch available chart types from backend
  useEffect(() => {
    fetch(`${API_BASE}/chart-types`)
      .then((r) => r.json())
      .then((data: ChartTypesResponse) => {
        const types = data.all ?? data.priority ?? [];
        setChartTypes(types);
        if (types.length > 0 && !types.includes(activeType)) {
          setActiveType(types[0]);
        }
        setServerOnline(true);
      })
      .catch(() => {
        // Server offline — show available types from known list for UI
        setServerOnline(false);
      });
  }, []);

  // When chart type changes, reset kw (keep file path and common labels)
  function handleSelectType(type: string) {
    setActiveType(type);
    // Reset rendered plot when switching type
    setRenderKw(null);
    setPendingKw((prev) => ({
      ...DEFAULT_KW,
      excel_path: prev.excel_path,
      title: prev.title,
      xlabel: prev.xlabel,
      ytitle: prev.ytitle,
      color: prev.color,
      font_size: prev.font_size,
    }));
  }

  function handleKwChange(updated: Record<string, unknown>) {
    setPendingKw(updated);
    // Auto-clear render if file removed
    if (!updated.excel_path) {
      setRenderKw(null);
    }
  }

  const handleGenerate = useCallback(() => {
    if (!pendingKw.excel_path) return;
    // Commit pendingKw and trigger a render
    setRenderKw({ ...pendingKw });
  }, [pendingKw]);

  const hasFile = Boolean(pendingKw.excel_path);

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <h1>Refraction</h1>
        <span className="app-header-sub">
          {serverOnline
            ? `${chartTypes.length} chart types`
            : 'Connecting to server…'}
        </span>
      </header>

      {/* Body */}
      <div className="app-body">
        {/* Left sidebar — chart type selector */}
        <Sidebar
          chartTypes={chartTypes}
          activeType={activeType}
          onSelect={handleSelectType}
        />

        {/* Center — chart display */}
        <main className="chart-area">
          <div className="chart-area-inner">
            {renderKw ? (
              <PlotterChart
                chartType={activeType}
                kw={renderKw}
              />
            ) : (
              <div className="chart-placeholder">
                <div className="chart-placeholder-icon">📊</div>
                <p>
                  {hasFile
                    ? 'Click "Generate Plot" to render'
                    : 'Upload a data file to get started'}
                </p>
              </div>
            )}
          </div>

          {/* Panel collapse button */}
          <button
            className={`panel-collapse-btn${configCollapsed ? ' panel-hidden' : ''}`}
            onClick={() => setConfigCollapsed((v) => !v)}
            title={configCollapsed ? 'Show config' : 'Hide config'}
          >
            {configCollapsed ? '◀' : '▶'}
          </button>
        </main>

        {/* Right config panel */}
        <ConfigPanel
          kw={pendingKw}
          onChange={handleKwChange}
          onGenerate={handleGenerate}
          collapsed={configCollapsed}
          onToggleCollapse={() => setConfigCollapsed((v) => !v)}
          hasFile={hasFile}
        />
      </div>
    </div>
  );
}

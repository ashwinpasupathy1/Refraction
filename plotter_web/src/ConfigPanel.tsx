import { FileUpload } from './FileUpload';

interface ConfigPanelProps {
  kw: Record<string, unknown>;
  onChange: (kw: Record<string, unknown>) => void;
  onGenerate: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  hasFile: boolean;
}

export function ConfigPanel({
  kw,
  onChange,
  onGenerate,
  collapsed,
  onToggleCollapse,
  hasFile,
}: ConfigPanelProps) {
  function set(key: string, value: unknown) {
    onChange({ ...kw, [key]: value });
  }

  function handleUploaded(path: string) {
    onChange({ ...kw, excel_path: path });
  }

  return (
    <aside className={`config-panel${collapsed ? ' collapsed' : ''}`}>
      <div className="config-panel-header">
        <h2>Configure</h2>
        <button
          className="config-panel-toggle"
          onClick={onToggleCollapse}
          title={collapsed ? 'Show panel' : 'Hide panel'}
        >
          {collapsed ? '◁' : '▷'}
        </button>
      </div>

      {!collapsed && (
        <div className="config-panel-body">
          {/* Data section */}
          <div className="config-section">
            <div className="config-section-title">Data</div>
            <div className="form-group">
              <label>Excel File (.xlsx)</label>
              <FileUpload onUploaded={handleUploaded} />
            </div>
            <div className="form-group">
              <label>Sheet</label>
              <input
                type="number"
                min={0}
                value={(kw.sheet as number) ?? 0}
                onChange={(e) => set('sheet', parseInt(e.target.value, 10) || 0)}
              />
            </div>
          </div>

          {/* Labels section */}
          <div className="config-section">
            <div className="config-section-title">Labels</div>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={(kw.title as string) ?? ''}
                onChange={(e) => set('title', e.target.value)}
                placeholder="Chart title"
              />
            </div>
            <div className="form-group">
              <label>X Label</label>
              <input
                type="text"
                value={(kw.xlabel as string) ?? ''}
                onChange={(e) => set('xlabel', e.target.value)}
                placeholder="X axis label"
              />
            </div>
            <div className="form-group">
              <label>Y Label</label>
              <input
                type="text"
                value={(kw.ytitle as string) ?? ''}
                onChange={(e) => set('ytitle', e.target.value)}
                placeholder="Y axis label"
              />
            </div>
          </div>

          {/* Style section */}
          <div className="config-section">
            <div className="config-section-title">Style</div>
            <div className="form-group">
              <label>Primary Color</label>
              <input
                type="color"
                value={(kw.color as string) ?? '#2274A5'}
                onChange={(e) => set('color', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Font Size</label>
              <input
                type="number"
                min={6}
                max={24}
                step={0.5}
                value={(kw.font_size as number) ?? 12}
                onChange={(e) => set('font_size', parseFloat(e.target.value) || 12)}
              />
            </div>
          </div>
        </div>
      )}

      {!collapsed && (
        <div className="config-panel-footer">
          <button
            className="btn-generate"
            onClick={onGenerate}
            disabled={!hasFile}
            title={hasFile ? 'Generate plot' : 'Upload a data file first'}
          >
            Generate Plot
          </button>
        </div>
      )}
    </aside>
  );
}

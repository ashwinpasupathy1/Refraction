import { useState } from 'react';

interface SidebarProps {
  chartTypes: string[];
  activeType: string;
  onSelect: (type: string) => void;
}

// ── Category definitions ─────────────────────────────────────────
const CATEGORIES: { label: string; keys: string[] }[] = [
  {
    label: 'Categorical',
    keys: [
      'bar', 'grouped_bar', 'stacked_bar', 'box', 'violin',
      'dot_plot', 'subcolumn_scatter', 'histogram', 'raincloud',
    ],
  },
  {
    label: 'Regression',
    keys: ['line', 'scatter', 'curve_fit', 'bubble', 'area_chart'],
  },
  {
    label: 'Paired',
    keys: ['before_after', 'repeated_measures'],
  },
  {
    label: 'Clinical',
    keys: ['kaplan_meier', 'bland_altman', 'forest_plot'],
  },
  {
    label: 'Statistical',
    keys: [
      'column_stats', 'contingency', 'chi_square_gof',
      'two_way_anova', 'ecdf', 'qq_plot',
    ],
  },
  {
    label: 'Other',
    keys: ['heatmap', 'lollipop', 'waterfall', 'pyramid'],
  },
];

// Convert snake_case key to human-readable label
function toLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bAova\b/, 'ANOVA')
    .replace(/\bGof\b/, 'GoF')
    .replace(/\bEcdf\b/, 'ECDF')
    .replace(/\bQq\b/, 'Q-Q')
    .replace(/\bKaplan Meier\b/, 'Survival Curve')
    .replace(/\bChi Square Gof\b/, 'Chi-Sq GoF')
    .replace(/\bTwo Way Anova\b/, 'Two-Way ANOVA')
    .replace(/\bBland Altman\b/, 'Bland-Altman')
    .replace(/\bForest Plot\b/, 'Forest Plot')
    .replace(/\bColumn Stats\b/, 'Col Statistics')
    .replace(/\bSubcolumn Scatter\b/, 'Subcolumn')
    .replace(/\bBefore After\b/, 'Before / After')
    .replace(/\bRepeated Measures\b/, 'Repeated Meas.')
    .replace(/\bArea Chart\b/, 'Area Chart');
}

export function Sidebar({ chartTypes, activeType, onSelect }: SidebarProps) {
  // Track which categories are collapsed
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  function toggleCategory(label: string) {
    setCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  }

  // For each category, filter to only the types present in chartTypes
  // (so the sidebar adapts to what the server actually supports)
  const renderedCategories = CATEGORIES.map((cat) => ({
    ...cat,
    items: cat.keys.filter((k) => chartTypes.includes(k)),
  })).filter((cat) => cat.items.length > 0);

  // Uncategorised types (not in any category definition)
  const categorisedKeys = new Set(CATEGORIES.flatMap((c) => c.keys));
  const uncategorised = chartTypes.filter((k) => !categorisedKeys.has(k));

  return (
    <nav className="sidebar">
      {renderedCategories.map((cat) => {
        const isOpen = !collapsed[cat.label];
        return (
          <div key={cat.label} className="sidebar-section">
            <div
              className="sidebar-category"
              onClick={() => toggleCategory(cat.label)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && toggleCategory(cat.label)}
            >
              {cat.label}
              <span className="sidebar-category-toggle">
                {isOpen ? '▾' : '▸'}
              </span>
            </div>
            {isOpen && (
              <ul className="sidebar-items">
                {cat.items.map((key) => (
                  <li key={key}>
                    <button
                      className={`sidebar-item${activeType === key ? ' active' : ''}`}
                      onClick={() => onSelect(key)}
                      title={toLabel(key)}
                    >
                      {toLabel(key)}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}

      {uncategorised.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-category">Other</div>
          <ul className="sidebar-items">
            {uncategorised.map((key) => (
              <li key={key}>
                <button
                  className={`sidebar-item${activeType === key ? ' active' : ''}`}
                  onClick={() => onSelect(key)}
                >
                  {toLabel(key)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </nav>
  );
}

// ChartType.swift — All Phase 1 chart types with metadata for sidebar grouping.

import Foundation

enum ChartCategory: String, CaseIterable, Identifiable {
    case column = "Column"
    case xy = "XY"
    case grouped = "Grouped"
    case distribution = "Distribution"

    var id: String { rawValue }
}

enum ChartType: String, CaseIterable, Identifiable {
    case bar
    case box
    case scatter
    case line
    case groupedBar = "grouped_bar"
    case violin
    case histogram
    case beforeAfter = "before_after"

    var id: String { rawValue }

    /// The API key sent to the Python server (matches _SPEC_BUILDERS keys).
    var key: String { rawValue }

    /// Human-readable label for the sidebar.
    var label: String {
        switch self {
        case .bar:         return "Bar Chart"
        case .box:         return "Box Plot"
        case .scatter:     return "Scatter Plot"
        case .line:        return "Line Graph"
        case .groupedBar:  return "Grouped Bar"
        case .violin:      return "Violin Plot"
        case .histogram:   return "Histogram"
        case .beforeAfter: return "Before / After"
        }
    }

    /// Sidebar category for grouping.
    var category: ChartCategory {
        switch self {
        case .bar, .box:                return .column
        case .scatter, .line:           return .xy
        case .groupedBar:               return .grouped
        case .violin, .histogram, .beforeAfter: return .distribution
        }
    }

    /// Whether this chart type supports jittered data points overlay.
    var hasPoints: Bool {
        switch self {
        case .bar, .box, .violin, .beforeAfter: return true
        default: return false
        }
    }

    /// Whether this chart type supports error bars (SEM/SD/CI95).
    var hasErrorBars: Bool {
        switch self {
        case .bar, .groupedBar: return true
        default: return false
        }
    }

    /// Whether this chart type supports statistical tests.
    var hasStats: Bool {
        switch self {
        case .histogram: return false
        default: return true
        }
    }

    /// SF Symbol name for the sidebar icon.
    var sfSymbol: String {
        switch self {
        case .bar:         return "chart.bar.fill"
        case .box:         return "square.fill"
        case .scatter:     return "circle.grid.cross.fill"
        case .line:        return "chart.xyaxis.line"
        case .groupedBar:  return "chart.bar.xaxis"
        case .violin:      return "waveform.path"
        case .histogram:   return "chart.bar.fill"
        case .beforeAfter: return "arrow.left.arrow.right"
        }
    }

    /// Chart types grouped by category for sidebar display.
    static var byCategory: [(category: ChartCategory, types: [ChartType])] {
        ChartCategory.allCases.compactMap { cat in
            let types = ChartType.allCases.filter { $0.category == cat }
            return types.isEmpty ? nil : (category: cat, types: types)
        }
    }
}

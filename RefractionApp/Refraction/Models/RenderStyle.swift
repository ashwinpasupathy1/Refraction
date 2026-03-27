// RenderStyle.swift — Predefined rendering style presets.
// Each preset configures FormatGraphSettings and FormatAxesSettings
// to mimic the visual style of popular plotting libraries.
// Purely client-side — no engine calls.

import Foundation

enum RenderStyle: String, CaseIterable, Identifiable, Codable {
    case `default` = "default"
    case prism = "prism"
    case ggplot2 = "ggplot2"
    case matplotlib = "matplotlib"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .default:    return "Default"
        case .prism:      return "Prism"
        case .ggplot2:    return "ggplot2"
        case .matplotlib: return "Matplotlib"
        }
    }

    var description: String {
        switch self {
        case .default:    return "Clean default style with light grid"
        case .prism:      return "GraphPad Prism: L-shaped axes, no grid, bold"
        case .ggplot2:    return "R ggplot2: gray background, white grid lines"
        case .matplotlib: return "Python matplotlib: full frame, dashed grid"
        }
    }

    // MARK: - Color Palettes

    var palette: [String] {
        switch self {
        case .default:
            return [
                "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
                "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
            ]
        case .prism:
            // GraphPad Prism 10 default palette (pure saturated, rendered at ~50% fill opacity)
            return [
                "#0000FF", "#FF0000", "#00C000", "#A020F0", "#FF8000",
                "#00BFFF", "#FF00FF", "#808000", "#00FF00", "#800000",
            ]
        case .ggplot2:
            // ggplot2 default (hue_pal) approximation
            return [
                "#F8766D", "#A3A500", "#00BF7D", "#00B0F6", "#E76BF3",
                "#D89000", "#39B600", "#00BFC4", "#9590FF", "#FF62BC",
            ]
        case .matplotlib:
            // matplotlib tab10
            return [
                "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
                "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
            ]
        }
    }

    // MARK: - Apply Preset

    /// Apply this render style to the given format settings.
    /// Preserves user-specific data (like axis titles) but sets all visual properties.
    func apply(to graph: FormatGraphSettings, axes: FormatAxesSettings) {
        switch self {
        case .default:
            applyDefault(graph: graph, axes: axes)
        case .prism:
            applyPrism(graph: graph, axes: axes)
        case .ggplot2:
            applyGgplot2(graph: graph, axes: axes)
        case .matplotlib:
            applyMatplotlib(graph: graph, axes: axes)
        }
    }

    // MARK: - Default

    private func applyDefault(graph: FormatGraphSettings, axes: FormatAxesSettings) {
        // Symbols
        graph.showSymbols = true
        graph.symbolColor = "#000000"
        graph.symbolShape = .circle
        graph.symbolSize = 6.0
        graph.symbolBorderColor = "#000000"
        graph.symbolBorderThickness = 0.8

        // Bars
        graph.showBars = true
        graph.barWidth = 0.6
        graph.barBorderColor = "#000000"
        graph.barBorderThickness = 0.8
        graph.barPattern = .solid

        // Error bars
        graph.showErrorBars = true
        graph.errorBarColor = "#222222"
        graph.errorBarThickness = 1.0
        graph.errorBarStyle = .tCap
        graph.errorBarDirection = .both

        // Lines
        graph.showConnectingLine = false
        graph.lineThickness = 1.5
        graph.lineStyle = .solid

        // Area
        graph.showAreaFill = false

        // Legend
        graph.showLegend = true

        // Axes — clean L-shape with light grid
        axes.axisThickness = 1.0
        axes.axisColor = "#000000"
        axes.plotAreaColor = "clear"
        axes.pageBackground = "clear"
        axes.frameStyle = .noFrame
        axes.hideAxes = .showBoth
        axes.majorGrid = .solid
        axes.majorGridColor = "#E5E5E5"
        axes.majorGridThickness = 0.5
        axes.minorGrid = .none
        axes.xAxisTickDirection = .out
        axes.yAxisTickDirection = .out
        axes.xAxisTickLength = 5
        axes.yAxisTickLength = 5
        axes.xAxisLabelRotation = 0
        axes.globalFontName = "Arial Bold"
        axes.chartTitleFontSize = 12
        axes.xAxisTitleFontSize = 12
        axes.yAxisTitleFontSize = 12
        axes.xAxisLabelFontSize = 12
        axes.yAxisLabelFontSize = 12
    }

    // MARK: - Prism
    // Matches GraphPad Prism 10 default appearance.

    private func applyPrism(graph: FormatGraphSettings, axes: FormatAxesSettings) {
        // Symbols — filled circles, same color as bar, no border (Prism default)
        graph.showSymbols = true
        graph.symbolColor = "auto"       // Uses group color (same as bar)
        graph.symbolShape = .circle
        graph.symbolSize = 7.0
        graph.symbolBorderColor = "#000000"
        graph.symbolBorderThickness = 0.0

        // Bars — saturated fill at ~50% opacity, solid full-color border
        graph.showBars = true
        graph.barWidth = 0.55            // Prism bars are moderately wide with clear gaps
        graph.barFillOpacity = 0.50      // Prism uses ~50% opacity fill
        graph.barBorderColor = "auto"    // Border matches group color (full saturation)
        graph.barBorderThickness = 1.5   // Visible solid border
        graph.barPattern = .solid

        // Error bars — black T-caps, thin
        graph.showErrorBars = true
        graph.errorBarColor = "#000000"
        graph.errorBarThickness = 1.0
        graph.errorBarStyle = .tCap
        graph.errorBarDirection = .both

        // Lines — solid, medium-bold
        graph.showConnectingLine = false
        graph.lineColor = "#000000"
        graph.lineThickness = 2.0
        graph.lineStyle = .solid

        // Area
        graph.showAreaFill = false

        // Legend
        graph.showLegend = true

        // Axes — L-shaped (left + bottom only), NO grid, bold spines
        axes.axisThickness = 2.0         // Prism uses thick axis lines
        axes.axisColor = "#000000"
        axes.plotAreaColor = "clear"
        axes.pageBackground = "clear"
        axes.frameStyle = .noFrame       // L-shape: left + bottom spines only
        axes.hideAxes = .showBoth
        axes.majorGrid = .none           // Prism: no gridlines by default
        axes.minorGrid = .none
        axes.xAxisTickDirection = .out    // Outward-facing ticks
        axes.yAxisTickDirection = .out
        axes.xAxisTickLength = 7
        axes.yAxisTickLength = 7
        axes.xAxisLabelRotation = 45     // Prism default: 45° rotated labels
        axes.globalFontName = "Arial Bold"
        axes.chartTitleFontSize = 14
        axes.xAxisTitleFontSize = 14
        axes.yAxisTitleFontSize = 14
        axes.xAxisLabelFontSize = 12
        axes.yAxisLabelFontSize = 12
    }

    // MARK: - ggplot2
    // Matches R ggplot2 default theme (theme_gray).

    private func applyGgplot2(graph: FormatGraphSettings, axes: FormatAxesSettings) {
        // Symbols — small filled circles, no border
        graph.showSymbols = true
        graph.symbolColor = "#000000"
        graph.symbolShape = .circle
        graph.symbolSize = 4.0
        graph.symbolBorderColor = "#000000"
        graph.symbolBorderThickness = 0.0

        // Bars — wide, no border
        graph.showBars = true
        graph.barWidth = 0.7
        graph.barBorderColor = "#000000"
        graph.barBorderThickness = 0.0
        graph.barPattern = .solid

        // Error bars — thin
        graph.showErrorBars = true
        graph.errorBarColor = "#333333"
        graph.errorBarThickness = 0.6
        graph.errorBarStyle = .tCap
        graph.errorBarDirection = .both

        // Lines — thin
        graph.showConnectingLine = false
        graph.lineThickness = 0.8
        graph.lineStyle = .solid

        // Area
        graph.showAreaFill = false

        // Legend
        graph.showLegend = true

        // Axes — NO visible spines, gray plot area, white grid lines
        axes.axisThickness = 0.0         // No visible axis lines
        axes.axisColor = "#636363"
        axes.plotAreaColor = "#EBEBEB"   // Signature gray background
        axes.pageBackground = "clear"
        axes.frameStyle = .noFrame
        axes.hideAxes = .showBoth
        axes.majorGrid = .solid
        axes.majorGridColor = "#FFFFFF"  // White gridlines on gray bg
        axes.majorGridThickness = 0.8
        axes.minorGrid = .none
        axes.xAxisTickDirection = .none  // No ticks in ggplot2
        axes.yAxisTickDirection = .none
        axes.xAxisTickLength = 0
        axes.yAxisTickLength = 0
        axes.xAxisLabelRotation = 0
        axes.globalFontName = "Arial Bold"
        axes.chartTitleFontSize = 12
        axes.xAxisTitleFontSize = 12
        axes.yAxisTitleFontSize = 12
        axes.xAxisLabelFontSize = 12
        axes.yAxisLabelFontSize = 12
    }

    // MARK: - Matplotlib
    // Matches Python matplotlib default (rcParams).

    private func applyMatplotlib(graph: FormatGraphSettings, axes: FormatAxesSettings) {
        // Symbols — medium with thin border
        graph.showSymbols = true
        graph.symbolColor = "#000000"
        graph.symbolShape = .circle
        graph.symbolSize = 6.0
        graph.symbolBorderColor = "#000000"
        graph.symbolBorderThickness = 0.5

        // Bars — thin black border (matplotlib default)
        graph.showBars = true
        graph.barWidth = 0.6
        graph.barBorderColor = "#000000"
        graph.barBorderThickness = 0.5
        graph.barPattern = .solid

        // Error bars — black lines, no caps (matplotlib default)
        graph.showErrorBars = true
        graph.errorBarColor = "#000000"
        graph.errorBarThickness = 1.0
        graph.errorBarStyle = .line      // matplotlib: no T-caps by default
        graph.errorBarDirection = .both

        // Lines — medium
        graph.showConnectingLine = false
        graph.lineThickness = 1.5
        graph.lineStyle = .solid

        // Area
        graph.showAreaFill = false

        // Legend
        graph.showLegend = true

        // Axes — full box frame, dashed grid
        axes.axisThickness = 1.0
        axes.axisColor = "#000000"
        axes.plotAreaColor = "clear"
        axes.pageBackground = "clear"
        axes.frameStyle = .plain         // Full box (all 4 spines)
        axes.hideAxes = .showBoth
        axes.majorGrid = .dashed
        axes.majorGridColor = "#CCCCCC"
        axes.majorGridThickness = 0.5
        axes.minorGrid = .none
        axes.xAxisTickDirection = .in     // matplotlib: inward ticks
        axes.yAxisTickDirection = .in
        axes.xAxisTickLength = 4
        axes.yAxisTickLength = 4
        axes.xAxisLabelRotation = 0
        axes.globalFontName = "Arial Bold" // DejaVu Sans not on macOS, Helvetica is close
        axes.chartTitleFontSize = 12
        axes.xAxisTitleFontSize = 12
        axes.yAxisTitleFontSize = 12
        axes.xAxisLabelFontSize = 12
        axes.yAxisLabelFontSize = 12
    }
}

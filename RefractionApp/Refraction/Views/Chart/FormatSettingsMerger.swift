// FormatSettingsMerger.swift — Merges app-layer FormatGraphSettings and
// FormatAxesSettings into the renderer's ChartSpec/StyleSpec/AxisSpec.
//
// This bridges the gap between the Format Graph / Format Axes dialogs
// (which bind to @Observable settings on each Graph) and the renderer
// package (which reads from ChartSpec structs decoded from engine JSON).
//
// The renderer package types (StyleSpec, AxisSpec, ChartSpec) are NOT
// modified — this function produces a new ChartSpec with overrides applied.

import Foundation
import RefractionRenderer

/// Produce a new `ChartSpec` with format dialog overrides merged in.
///
/// The engine-provided spec is the baseline; any non-default format setting
/// wins. This lets Format Graph / Format Axes changes take immediate effect
/// without re-running the analysis engine.
func applyFormatSettings(
    spec: ChartSpec,
    graphSettings: FormatGraphSettings,
    axesSettings: FormatAxesSettings,
    renderStyle: RenderStyle = .default
) -> ChartSpec {

    // ── StyleSpec overrides ──────────────────────────────────────────

    let mergedStyle = StyleSpec(
        colors: renderStyle.palette,
        showPoints: graphSettings.showSymbols,
        showBrackets: spec.style.showBrackets,
        pointSize: graphSettings.symbolSize,
        pointAlpha: spec.style.pointAlpha,
        barWidth: graphSettings.barWidth,
        errorType: graphSettings.showErrorBars ? spec.style.errorType : "none",
        axisStyle: mapFrameStyle(axesSettings.frameStyle),
        symbolShape: graphSettings.symbolShape.rawValue,
        symbolColor: graphSettings.symbolColor,
        symbolBorderColor: graphSettings.symbolBorderColor,
        symbolBorderThickness: graphSettings.symbolBorderThickness,
        showBars: graphSettings.showBars,
        barFillOpacity: graphSettings.barFillOpacity,
        barBorderColor: graphSettings.barBorderColor,
        barBorderThickness: graphSettings.barBorderThickness,
        errorBarColor: graphSettings.errorBarColor,
        errorBarDirection: graphSettings.errorBarDirection.rawValue,
        errorBarStyle: graphSettings.errorBarStyle.rawValue,
        errorBarThickness: graphSettings.errorBarThickness,
        showConnectingLine: graphSettings.showConnectingLine,
        lineColor: graphSettings.lineColor,
        lineThickness: graphSettings.lineThickness,
        lineStyle: graphSettings.lineStyle.rawValue,
        showAreaFill: graphSettings.showAreaFill,
        areaFillColor: graphSettings.areaFillColor,
        areaFillPosition: graphSettings.areaFillPosition.rawValue,
        areaFillAlpha: graphSettings.areaFillAlpha,
        showLegend: graphSettings.showLegend
    )

    // ── AxisSpec overrides ───────────────────────────────────────────

    // Title: prefer format dialog value if non-empty, else engine value
    let title = axesSettings.chartTitle.isEmpty ? spec.axes.title : axesSettings.chartTitle
    let xLabel = axesSettings.xAxisTitle.isEmpty ? spec.axes.xLabel : axesSettings.xAxisTitle
    let yLabel = axesSettings.yAxisTitle.isEmpty ? spec.axes.yLabel : axesSettings.yAxisTitle

    // Y range: if user disabled auto-range, use their manual min/max
    let yRange: [Double]?
    if !axesSettings.yAxisAutoRange {
        yRange = [axesSettings.yAxisMin, axesSettings.yAxisMax]
    } else {
        yRange = spec.axes.yRange
    }

    // Y scale
    let yScale: String
    switch axesSettings.yAxisScale {
    case .linear: yScale = "linear"
    case .log:    yScale = "log"
    }

    // Y-axis tick direction
    let yTickDirection: String
    switch axesSettings.yAxisTickDirection {
    case .out:  yTickDirection = "out"
    case .in:   yTickDirection = "in"
    case .both: yTickDirection = "inout"
    case .none: yTickDirection = "none"
    }

    // X-axis tick direction
    let xTickDirection: String
    switch axesSettings.xAxisTickDirection {
    case .out:  xTickDirection = "out"
    case .in:   xTickDirection = "in"
    case .both: xTickDirection = "inout"
    case .none: xTickDirection = "none"
    }

    // Hide axes
    let hideAxes = axesSettings.hideAxes.rawValue

    // Grid lines
    let majorGrid = axesSettings.majorGrid.rawValue
    let minorGrid = axesSettings.minorGrid.rawValue

    let mergedAxes = AxisSpec(
        title: title,
        xLabel: xLabel,
        yLabel: yLabel,
        xScale: spec.axes.xScale,
        yScale: yScale,
        xRange: spec.axes.xRange,
        yRange: yRange,
        yTicks: spec.axes.yTicks,
        yTickLabels: spec.axes.yTickLabels,
        tickDirection: yTickDirection,
        spineWidth: axesSettings.axisThickness,
        fontSize: axesSettings.chartTitleFontSize,
        axisColor: axesSettings.axisColor,
        xTickDirection: xTickDirection,
        xTickLength: axesSettings.xAxisTickLength,
        yTickLength: axesSettings.yAxisTickLength,
        titleFontSize: axesSettings.chartTitleFontSize,
        xLabelFontSize: axesSettings.xAxisTitleFontSize,
        yLabelFontSize: axesSettings.yAxisTitleFontSize,
        xTickLabelFontSize: axesSettings.xAxisLabelFontSize,
        yTickLabelFontSize: axesSettings.yAxisLabelFontSize,
        xLabelRotation: axesSettings.xAxisLabelRotation,
        hideAxes: hideAxes,
        majorGrid: majorGrid,
        majorGridColor: axesSettings.majorGridColor,
        majorGridThickness: axesSettings.majorGridThickness,
        minorGrid: minorGrid,
        minorGridColor: axesSettings.minorGridColor,
        minorGridThickness: axesSettings.minorGridThickness,
        plotAreaColor: axesSettings.plotAreaColor,
        pageBackground: axesSettings.pageBackground,
        globalFontName: axesSettings.globalFontName
    )

    // ── Assemble merged ChartSpec ────────────────────────────────────

    return ChartSpec(
        chartType: spec.chartType,
        groups: spec.groups,
        style: mergedStyle,
        axes: mergedAxes,
        stats: spec.stats,
        brackets: spec.brackets,
        referenceLine: spec.referenceLine,
        data: spec.data
    )
}

// MARK: - Helpers

/// Map FormatAxesSettings.FrameStyle to the string the AxisRenderer expects.
private func mapFrameStyle(_ frame: FormatAxesSettings.FrameStyle) -> String {
    switch frame {
    case .noFrame: return "open"
    case .plain:   return "closed"
    case .shadow:  return "closed"
    }
}

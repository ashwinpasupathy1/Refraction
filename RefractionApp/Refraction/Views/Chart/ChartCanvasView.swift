// ChartCanvasView.swift — SwiftUI Canvas that renders a ChartSpec
// using native Core Graphics via the renderer modules.

import SwiftUI
import RefractionRenderer

struct ChartCanvasView: View {

    let spec: ChartSpec

    /// Insets from the canvas edge to the plot area (axes region).
    private let plotInsets = EdgeInsets(top: 40, leading: 60, bottom: 50, trailing: 20)

    /// Ideal plot width per group slot for bar-like charts (Prism-style fixed bar sizing).
    private static let idealSlotWidth: CGFloat = 90.0

    /// Whether this chart type uses fixed-width bar slots (vs filling the plot area).
    private var usesFixedBarSlots: Bool {
        ["bar", "column_stats", "waterfall", "pyramid", "box", "violin",
         "dot_plot", "raincloud", "histogram", "before_after", "lollipop"].contains(spec.chartType)
    }

    var body: some View {
        GeometryReader { geometry in
            Canvas { context, size in
                // For bar-like charts, compute a fixed plot width from group count
                // so bars don't stretch. Center the plot area horizontally.
                let maxPlotWidth = size.width - plotInsets.leading - plotInsets.trailing
                let plotWidth: CGFloat
                let plotX: CGFloat

                if usesFixedBarSlots && !spec.groups.isEmpty {
                    let idealWidth = Self.idealSlotWidth * CGFloat(spec.groups.count)
                    plotWidth = min(idealWidth, maxPlotWidth)
                    plotX = plotInsets.leading + (maxPlotWidth - plotWidth) / 2
                } else {
                    plotWidth = maxPlotWidth
                    plotX = plotInsets.leading
                }

                let plotRect = CGRect(
                    x: plotX,
                    y: plotInsets.top,
                    width: plotWidth,
                    height: size.height - plotInsets.top - plotInsets.bottom
                )

                // Compute Y range that accounts for both engine range and raw data points.
                // The engine may only consider mean±error; raw scatter points can exceed that.
                let dataRange = RefractionRenderer.computeYRange(groups: spec.groups, errorType: spec.style.errorType)
                let yRange: (min: Double, max: Double)
                if let r = spec.axes.yRange, r.count == 2 {
                    // Expand engine range if raw data points exceed it
                    yRange = (min: Swift.min(r[0], dataRange.min), max: Swift.max(r[1], dataRange.max))
                } else {
                    yRange = dataRange
                }

                // 1. Draw axis background and grid (behind chart data)
                AxisRenderer.drawBackground(
                    in: context,
                    plotRect: plotRect,
                    spec: spec.axes,
                    style: spec.style,
                    yRange: yRange
                )

                // 2. Dispatch to the appropriate chart renderer
                switch spec.chartType {

                // ── Working renderers ────────────────────────────

                case "bar", "column_stats", "waterfall", "pyramid":
                    BarRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style,
                        yRangeOverride: yRange
                    )

                case "grouped_bar":
                    GroupedBarRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        style: spec.style
                    )

                case "stacked_bar":
                    StackedBarRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        style: spec.style
                    )

                case "box":
                    BoxRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        groups: spec.groups,
                        style: spec.style
                    )

                case "violin":
                    ViolinRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        groups: spec.groups,
                        style: spec.style
                    )

                case "scatter":
                    ScatterRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style,
                        data: spec.data
                    )

                case "line":
                    LineRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style,
                        data: spec.data
                    )

                case "histogram":
                    HistogramRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        groups: spec.groups,
                        style: spec.style
                    )

                case "before_after":
                    BeforeAfterRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style
                    )

                case "dot_plot", "subcolumn_scatter":
                    DotPlotRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style
                    )

                // ── Not yet implemented — show placeholder ──────

                case "kaplan_meier":
                    KaplanMeierRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        spec: spec,
                        style: spec.style
                    )

                case "area_chart":
                    AreaChartRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "curve_fit":
                    CurveFitRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "bubble":
                    BubbleRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "lollipop":
                    LollipopRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style
                    )

                case "ecdf":
                    ECDFRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "qq_plot":
                    QQPlotRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "raincloud":
                    RaincloudRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "forest_plot":
                    ForestPlotRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "bland_altman":
                    BlandAltmanRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "contingency":
                    ContingencyRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "chi_square_gof":
                    ChiSquareGoFRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "heatmap":
                    HeatmapRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "two_way_anova":
                    TwoWayAnovaRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                case "repeated_measures":
                    RepeatedMeasuresRenderer.draw(
                        in: context, plotRect: plotRect,
                        groups: spec.groups, style: spec.style, data: spec.data
                    )

                default:
                    if !spec.groups.isEmpty {
                        BarRenderer.draw(
                            in: context,
                            plotRect: plotRect,
                            groups: spec.groups,
                            style: spec.style,
                            yRangeOverride: yRange
                        )
                    } else {
                        drawPlaceholder(in: context, size: size, chartType: spec.chartType)
                    }
                }

                // 3. Draw significance brackets
                if spec.style.showBrackets && !spec.brackets.isEmpty {
                    BracketRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        brackets: spec.brackets,
                        groupCount: spec.groups.count,
                        style: spec.style,
                        groups: spec.groups
                    )
                }

                // 4. Draw reference line
                if let refLine = spec.referenceLine {
                    drawReferenceLine(in: context, plotRect: plotRect, refLine: refLine, spec: spec)
                }

                // 5. Draw axis spines, ticks, and labels ON TOP of chart data
                AxisRenderer.drawForeground(
                    in: context,
                    plotRect: plotRect,
                    canvasSize: size,
                    spec: spec.axes,
                    style: spec.style,
                    groups: spec.groups.map(\.name),
                    yRange: yRange
                )
            }
            .background(pageBackgroundColor)
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .shadow(color: .black.opacity(0.1), radius: 2, x: 0, y: 1)
            .padding()
        }
    }

    /// Page background color from axes settings, defaulting to white.
    private var pageBackgroundColor: Color {
        let bg = spec.axes.pageBackground
        if bg == "clear" || bg.isEmpty { return .white }
        return Color(hex: bg)
    }

    // MARK: - Fallback

    private func drawPlaceholder(in context: GraphicsContext, size: CGSize, chartType: String) {
        let text = Text("Renderer for '\(chartType)' coming soon")
            .font(.title3)
            .foregroundStyle(.secondary)
        context.draw(text, at: CGPoint(x: size.width / 2, y: size.height / 2))
    }

    // MARK: - Reference line

    private func drawReferenceLine(
        in context: GraphicsContext,
        plotRect: CGRect,
        refLine: ReferenceLine,
        spec: ChartSpec
    ) {
        let yRange = computeYRange(groups: spec.groups)
        guard yRange.max > yRange.min else { return }

        let fraction = (refLine.y - yRange.min) / (yRange.max - yRange.min)
        let yPos = plotRect.maxY - fraction * plotRect.height

        guard yPos >= plotRect.minY && yPos <= plotRect.maxY else { return }

        var path = Path()
        path.move(to: CGPoint(x: plotRect.minX, y: yPos))
        path.addLine(to: CGPoint(x: plotRect.maxX, y: yPos))

        context.stroke(
            path,
            with: .color(.gray.opacity(0.6)),
            style: StrokeStyle(lineWidth: 1, dash: [6, 4])
        )

        if !refLine.label.isEmpty {
            let label = Text(refLine.label)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
            context.draw(label, at: CGPoint(x: plotRect.maxX - 4, y: yPos - 10), anchor: .trailing)
        }
    }

    private func computeYRange(groups: [GroupData]) -> (min: Double, max: Double) {
        var allValues: [Double] = []
        for g in groups {
            if let mean = g.values.mean {
                allValues.append(mean)
                if let sem = g.values.sem {
                    allValues.append(mean + sem)
                }
            }
            allValues.append(contentsOf: g.values.raw)
        }
        guard !allValues.isEmpty else { return (0, 1) }
        let lo = allValues.min()!
        let hi = allValues.max()!
        let padding = (hi - lo) * 0.1
        return (min(lo, 0), hi + padding)
    }
}

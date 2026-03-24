// ChartCanvasView.swift — SwiftUI Canvas that renders the current ChartSpec
// using native Core Graphics via the renderer modules.

import SwiftUI

struct ChartCanvasView: View {

    @Environment(AppState.self) private var appState

    /// Insets from the canvas edge to the plot area (axes region).
    private let plotInsets = EdgeInsets(top: 40, leading: 60, bottom: 50, trailing: 20)

    var body: some View {
        GeometryReader { geometry in
            Canvas { context, size in
                guard let spec = appState.currentSpec else { return }

                let plotRect = CGRect(
                    x: plotInsets.leading,
                    y: plotInsets.top,
                    width: size.width - plotInsets.leading - plotInsets.trailing,
                    height: size.height - plotInsets.top - plotInsets.bottom
                )

                // 1. Draw axes (spines, ticks, labels)
                AxisRenderer.draw(
                    in: context,
                    plotRect: plotRect,
                    canvasSize: size,
                    spec: spec.axes,
                    style: spec.style,
                    groups: spec.groups.map(\.name)
                )

                // 2. Dispatch to the appropriate chart renderer
                switch spec.chartType {
                case "bar", "grouped_bar":
                    BarRenderer.draw(
                        in: context,
                        plotRect: plotRect,
                        groups: spec.groups,
                        style: spec.style
                    )
                default:
                    // Fallback: draw bars for any chart type with group data
                    if !spec.groups.isEmpty {
                        BarRenderer.draw(
                            in: context,
                            plotRect: plotRect,
                            groups: spec.groups,
                            style: spec.style
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
                        style: spec.style
                    )
                }

                // 4. Draw reference line
                if let refLine = spec.referenceLine {
                    drawReferenceLine(in: context, plotRect: plotRect, refLine: refLine, spec: spec)
                }
            }
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .shadow(color: .black.opacity(0.1), radius: 2, x: 0, y: 1)
            .padding()
        }
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
        // Compute Y position from data range
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

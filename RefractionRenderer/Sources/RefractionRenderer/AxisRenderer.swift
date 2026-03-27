// AxisRenderer.swift — Draws Prism-style open spines, tick marks,
// axis labels, and chart title using SwiftUI Canvas + Core Graphics.
// Uses prettyTicks() for nice Y-axis tick placement.

import SwiftUI

public enum AxisRenderer {

    /// Draw axes (spines, ticks, labels, title) into the canvas context.
    /// Call `draw` for the full axis pass, or use `drawBackground` + `drawForeground` separately
    /// to render chart data between them (so spines draw on top of bars).
    public static func draw(
        in context: GraphicsContext,
        plotRect: CGRect,
        canvasSize: CGSize,
        spec: AxisSpec,
        style: StyleSpec,
        groups: [String],
        yRange: (min: Double, max: Double)? = nil
    ) {
        drawBackground(in: context, plotRect: plotRect, spec: spec, style: style, yRange: yRange)
        drawForeground(in: context, plotRect: plotRect, canvasSize: canvasSize, spec: spec,
                       style: style, groups: groups, yRange: yRange)
    }

    /// Phase 1: Draw plot area background and grid lines (call BEFORE chart data).
    public static func drawBackground(
        in context: GraphicsContext,
        plotRect: CGRect,
        spec: AxisSpec,
        style: StyleSpec,
        yRange: (min: Double, max: Double)? = nil
    ) {
        // MARK: - Plot area background

        if spec.plotAreaColor != "clear" {
            let bgRect = Path(plotRect)
            context.fill(bgRect, with: .color(Color(hex: spec.plotAreaColor)))
        }

        // MARK: - Grid lines (drawn before data, behind everything)

        let yR = resolveYRange(spec: spec, yRange: yRange)
        let ticks = resolveTicks(spec: spec, yRange: yR)

        drawGridLines(
            in: context,
            plotRect: plotRect,
            ticks: ticks.values,
            yRange: yR,
            majorGrid: spec.majorGrid,
            majorGridColor: spec.majorGridColor,
            majorGridThickness: spec.majorGridThickness,
            minorGrid: spec.minorGrid,
            minorGridColor: spec.minorGridColor,
            minorGridThickness: spec.minorGridThickness
        )
    }

    /// Phase 2: Draw spines, ticks, labels, and titles (call AFTER chart data).
    public static func drawForeground(
        in context: GraphicsContext,
        plotRect: CGRect,
        canvasSize: CGSize,
        spec: AxisSpec,
        style: StyleSpec,
        groups: [String],
        yRange: (min: Double, max: Double)? = nil
    ) {
        let spineColor = Color(hex: spec.axisColor)
        let lineWidth = spec.spineWidth

        let hideX = spec.hideAxes == "hide_x" || spec.hideAxes == "hide_both"
        let hideY = spec.hideAxes == "hide_y" || spec.hideAxes == "hide_both"

        let yR = resolveYRange(spec: spec, yRange: yRange)
        let resolved = resolveTicks(spec: spec, yRange: yR)
        let ticks = resolved.values
        let tickLabels = resolved.labels

        // MARK: - Spines

        if !hideY {
            switch style.axisStyle {
            case "open":
                drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.topLeft,
                         color: spineColor, width: lineWidth)
            case "closed":
                drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.topLeft,
                         color: spineColor, width: lineWidth)
                drawLine(in: context, from: plotRect.bottomRight, to: plotRect.topRight,
                         color: spineColor, width: lineWidth)
            case "floating":
                let offset: CGFloat = 4
                drawLine(in: context,
                         from: CGPoint(x: plotRect.minX - offset, y: plotRect.maxY + offset),
                         to: CGPoint(x: plotRect.minX - offset, y: plotRect.minY),
                         color: spineColor, width: lineWidth)
            default:
                break
            }
        }

        if !hideX {
            switch style.axisStyle {
            case "open":
                drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.bottomRight,
                         color: spineColor, width: lineWidth)
            case "closed":
                drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.bottomRight,
                         color: spineColor, width: lineWidth)
                drawLine(in: context, from: plotRect.topLeft, to: plotRect.topRight,
                         color: spineColor, width: lineWidth)
            case "floating":
                let offset: CGFloat = 4
                drawLine(in: context,
                         from: CGPoint(x: plotRect.minX - offset, y: plotRect.maxY + offset),
                         to: CGPoint(x: plotRect.maxX, y: plotRect.maxY + offset),
                         color: spineColor, width: lineWidth)
            default:
                break
            }
        }

        // MARK: - Y-axis ticks

        let yTickLen = CGFloat(spec.yTickLength)

        if !hideY {
            for (idx, tickVal) in ticks.enumerated() {
                let y = yToCanvas(tickVal, plotRect: plotRect, yRange: yR)

                // Skip ticks outside the plot area
                guard y >= plotRect.minY - 1 && y <= plotRect.maxY + 1 else { continue }

                // Tick mark
                let tickStart: CGPoint
                let tickEnd: CGPoint

                switch spec.tickDirection {
                case "out":
                    tickStart = CGPoint(x: plotRect.minX, y: y)
                    tickEnd = CGPoint(x: plotRect.minX - yTickLen, y: y)
                case "in":
                    tickStart = CGPoint(x: plotRect.minX, y: y)
                    tickEnd = CGPoint(x: plotRect.minX + yTickLen, y: y)
                case "inout":
                    tickStart = CGPoint(x: plotRect.minX - yTickLen / 2, y: y)
                    tickEnd = CGPoint(x: plotRect.minX + yTickLen / 2, y: y)
                default:
                    continue
                }

                drawLine(in: context, from: tickStart, to: tickEnd,
                         color: spineColor, width: 0.8)

                // Tick label
                let labelText = idx < tickLabels.count ? tickLabels[idx] : formatTickValue(tickVal)
                let label = Text(labelText)
                    .font(.system(size: CGFloat(spec.yTickLabelFontSize)))
                    .foregroundStyle(Color(hex: spec.axisColor))
                context.draw(label, at: CGPoint(x: plotRect.minX - yTickLen - 4, y: y), anchor: .trailing)
            }
        }

        // MARK: - X-axis category labels

        if !hideX && !groups.isEmpty {
            let groupWidth = plotRect.width / CGFloat(groups.count)
            let xTickLen = CGFloat(spec.xTickLength)

            for (i, name) in groups.enumerated() {
                let x = plotRect.minX + (CGFloat(i) + 0.5) * groupWidth
                let y = plotRect.maxY

                // X tick marks
                let xTickDir = spec.xTickDirection
                if xTickDir != "none" {
                    let tickY: CGFloat
                    switch xTickDir {
                    case "out":   tickY = y + xTickLen
                    case "in":    tickY = y - xTickLen
                    case "inout":
                        drawLine(in: context,
                                 from: CGPoint(x: x, y: y - xTickLen / 2),
                                 to: CGPoint(x: x, y: y + xTickLen / 2),
                                 color: spineColor, width: 0.8)
                        // Draw label below the inout tick
                        drawXLabel(in: context, name: name, x: x, y: y + xTickLen / 2 + 8,
                                   fontSize: spec.xTickLabelFontSize, color: spec.axisColor,
                                   rotation: spec.xLabelRotation)
                        continue
                    default:      tickY = y + xTickLen
                    }
                    drawLine(in: context,
                             from: CGPoint(x: x, y: y),
                             to: CGPoint(x: x, y: tickY),
                             color: spineColor, width: 0.8)
                }

                drawXLabel(in: context, name: name, x: x, y: y + xTickLen + 8,
                           fontSize: spec.xTickLabelFontSize, color: spec.axisColor,
                           rotation: spec.xLabelRotation)
            }
        }

        // MARK: - Axis labels

        if !hideX && !spec.xLabel.isEmpty {
            let xLabelText = Text(spec.xLabel)
                .font(.system(size: CGFloat(spec.xLabelFontSize)))
                .foregroundStyle(Color(hex: spec.axisColor))
            context.draw(
                xLabelText,
                at: CGPoint(x: plotRect.midX, y: canvasSize.height - 8),
                anchor: .bottom
            )
        }

        if !hideY && !spec.yLabel.isEmpty {
            var yContext = context
            let yLabelPos = CGPoint(x: 14, y: plotRect.midY)
            yContext.translateBy(x: yLabelPos.x, y: yLabelPos.y)
            yContext.rotate(by: .degrees(-90))

            let yLabelText = Text(spec.yLabel)
                .font(.system(size: CGFloat(spec.yLabelFontSize)))
                .foregroundStyle(Color(hex: spec.axisColor))
            yContext.draw(yLabelText, at: .zero, anchor: .center)
        }

        // MARK: - Title

        if !spec.title.isEmpty {
            let titleText = Text(spec.title)
                .font(.system(size: CGFloat(spec.titleFontSize), weight: .semibold))
                .foregroundStyle(Color(hex: spec.axisColor))
            context.draw(titleText, at: CGPoint(x: plotRect.midX, y: 16), anchor: .top)
        }
    }

    // MARK: - Helpers for resolving Y range and ticks

    private static func resolveYRange(
        spec: AxisSpec,
        yRange: (min: Double, max: Double)? = nil
    ) -> (min: Double, max: Double) {
        if let range = spec.yRange, range.count == 2 {
            return (min: range[0], max: range[1])
        } else if let yr = yRange {
            return yr
        }
        return (min: 0, max: 10)
    }

    private static func resolveTicks(
        spec: AxisSpec,
        yRange: (min: Double, max: Double)
    ) -> (values: [Double], labels: [String]) {
        if !spec.yTicks.isEmpty {
            let labels = spec.yTickLabels.isEmpty
                ? spec.yTicks.map { formatTickValue($0) }
                : spec.yTickLabels
            return (values: spec.yTicks, labels: labels)
        } else {
            let t = prettyTicks(lo: yRange.min, hi: yRange.max)
            return (values: t, labels: t.map { formatTickValue($0) })
        }
    }

    // MARK: - Grid Lines

    private static func drawGridLines(
        in context: GraphicsContext,
        plotRect: CGRect,
        ticks: [Double],
        yRange: (min: Double, max: Double),
        majorGrid: String,
        majorGridColor: String,
        majorGridThickness: Double,
        minorGrid: String,
        minorGridColor: String,
        minorGridThickness: Double
    ) {
        // Major grid at each tick position
        if majorGrid != "none" {
            let dashStyle = gridStrokeStyle(majorGrid, thickness: majorGridThickness)
            let color = Color(hex: majorGridColor)

            for tickVal in ticks {
                let y = yToCanvas(tickVal, plotRect: plotRect, yRange: yRange)
                guard y >= plotRect.minY - 1 && y <= plotRect.maxY + 1 else { continue }

                var path = Path()
                path.move(to: CGPoint(x: plotRect.minX, y: y))
                path.addLine(to: CGPoint(x: plotRect.maxX, y: y))
                context.stroke(path, with: .color(color), style: dashStyle)
            }
        }

        // Minor grid: subdivide between major ticks
        if minorGrid != "none" && ticks.count >= 2 {
            let dashStyle = gridStrokeStyle(minorGrid, thickness: minorGridThickness)
            let color = Color(hex: minorGridColor)
            let majorStep = ticks.count >= 2 ? ticks[1] - ticks[0] : 1.0
            let minorStep = majorStep / 5.0

            var val = ticks.first! - majorStep
            let maxVal = ticks.last! + majorStep
            while val <= maxVal {
                // Skip if this aligns with a major tick
                let isMajor = ticks.contains(where: { abs($0 - val) < minorStep * 0.1 })
                if !isMajor {
                    let y = yToCanvas(val, plotRect: plotRect, yRange: yRange)
                    if y >= plotRect.minY - 1 && y <= plotRect.maxY + 1 {
                        var path = Path()
                        path.move(to: CGPoint(x: plotRect.minX, y: y))
                        path.addLine(to: CGPoint(x: plotRect.maxX, y: y))
                        context.stroke(path, with: .color(color), style: dashStyle)
                    }
                }
                val += minorStep
            }
        }
    }

    /// Convert grid style string to a StrokeStyle with optional dash pattern.
    private static func gridStrokeStyle(_ style: String, thickness: Double) -> StrokeStyle {
        let lw = CGFloat(thickness)
        switch style {
        case "dashed": return StrokeStyle(lineWidth: lw, dash: [6, 4])
        case "dotted": return StrokeStyle(lineWidth: lw, dash: [2, 3])
        default:       return StrokeStyle(lineWidth: lw)
        }
    }

    // MARK: - X Label with rotation

    private static func drawXLabel(
        in context: GraphicsContext,
        name: String,
        x: CGFloat,
        y: CGFloat,
        fontSize: Double,
        color: String,
        rotation: Double
    ) {
        let label = Text(name)
            .font(.system(size: CGFloat(fontSize)))
            .foregroundStyle(Color(hex: color))

        if rotation > 0 {
            var rotContext = context
            rotContext.translateBy(x: x, y: y)
            rotContext.rotate(by: .degrees(-rotation))
            rotContext.draw(label, at: .zero, anchor: .trailing)
        } else {
            context.draw(label, at: CGPoint(x: x, y: y), anchor: .top)
        }
    }
}

// BarRenderer.swift — Draws bar charts with error bars and jittered data
// points using SwiftUI Canvas + Core Graphics.
//
// Extracted from RefractionApp into the RefractionRenderer Swift Package.

import SwiftUI

public enum BarRenderer {

    /// Draw bars, error bars, and optional data points.
    public static func draw(
        in context: GraphicsContext,
        plotRect: CGRect,
        groups: [GroupData],
        style: StyleSpec,
        yRangeOverride: (min: Double, max: Double)? = nil
    ) {
        guard !groups.isEmpty else { return }

        let yRange = yRangeOverride ?? computeYRange(groups: groups, errorType: style.errorType)
        let barFraction = CGFloat(style.barWidth)

        // Use the same groupWidth as AxisRenderer (plotRect.width / count)
        // so bars are always centered on their x-axis label.
        // Cap the actual bar pixel width for Prism-like appearance.
        let groupWidth = plotRect.width / CGFloat(groups.count)
        let maxBarWidth: CGFloat = 50.0
        let barW = min(groupWidth * barFraction, maxBarWidth)

        for (i, group) in groups.enumerated() {
            let color = Color(hex: colorForIndex(i, style: style))
            let centerX = plotRect.minX + (CGFloat(i) + 0.5) * groupWidth

            guard let mean = group.values.mean else { continue }

            // Draw bar (only if showBars is true)
            if style.showBars {
                let barTop = yToCanvas(mean, plotRect: plotRect, yRange: yRange)
                let barBottom = yToCanvas(max(yRange.min, 0), plotRect: plotRect, yRange: yRange)

                // Clip bar to plot area so it doesn't draw over axis lines
                let rawBarRect = CGRect(
                    x: centerX - barW / 2,
                    y: min(barTop, barBottom),
                    width: barW,
                    height: abs(barBottom - barTop)
                )
                let barRect = rawBarRect.intersection(plotRect)
                guard !barRect.isNull else { continue }

                context.fill(Path(barRect), with: .color(color.opacity(style.barFillOpacity)))

                // Bar border ("auto" = use group color at full opacity)
                // Only draw the 3 visible sides (left, top, right) — not the bottom which sits on the axis
                let borderColor = style.barBorderColor == "auto" ? color : Color(hex: style.barBorderColor)
                if style.barBorderThickness > 0 {
                    var borderPath = Path()
                    // Left side
                    borderPath.move(to: CGPoint(x: barRect.minX, y: barRect.maxY))
                    borderPath.addLine(to: CGPoint(x: barRect.minX, y: barRect.minY))
                    // Top side
                    borderPath.addLine(to: CGPoint(x: barRect.maxX, y: barRect.minY))
                    // Right side
                    borderPath.addLine(to: CGPoint(x: barRect.maxX, y: barRect.maxY))
                    context.stroke(borderPath, with: .color(borderColor),
                                   lineWidth: CGFloat(style.barBorderThickness))
                }
            }

            // Error bars (only if errorType != "none")
            if style.errorType != "none" {
                let errorHalf = errorValue(for: group, errorType: style.errorType)
                if errorHalf > 0 {
                    drawErrorBar(
                        in: context,
                        centerX: centerX,
                        mean: mean,
                        errorHalf: errorHalf,
                        plotRect: plotRect,
                        yRange: yRange,
                        capWidth: barW * 0.4,
                        style: style
                    )
                }
            }

            // Data points
            if style.showPoints {
                let pointColor: Color
                if style.symbolColor == "auto" || style.symbolColor == "#000000" {
                    pointColor = color
                } else {
                    pointColor = Color(hex: style.symbolColor)
                }

                drawDataPoints(
                    in: context,
                    values: group.values.raw,
                    centerX: centerX,
                    plotRect: plotRect,
                    yRange: yRange,
                    color: pointColor,
                    pointSize: CGFloat(style.pointSize),
                    alpha: style.pointAlpha,
                    jitterWidth: barW * 0.3,
                    shape: style.symbolShape,
                    borderColor: Color(hex: style.symbolBorderColor),
                    borderThickness: CGFloat(style.symbolBorderThickness)
                )
            }
        }
    }

    // MARK: - Error bars

    private static func drawErrorBar(
        in context: GraphicsContext,
        centerX: CGFloat,
        mean: Double,
        errorHalf: Double,
        plotRect: CGRect,
        yRange: (min: Double, max: Double),
        capWidth: CGFloat,
        style: StyleSpec
    ) {
        let lineColor = Color(hex: style.errorBarColor)
        let thickness = CGFloat(style.errorBarThickness)
        let direction = style.errorBarDirection
        let hasCap = style.errorBarStyle == "t_cap"

        let meanY = yToCanvas(mean, plotRect: plotRect, yRange: yRange)
        let topY = yToCanvas(mean + errorHalf, plotRect: plotRect, yRange: yRange)
        let bottomY = yToCanvas(mean - errorHalf, plotRect: plotRect, yRange: yRange)

        // Draw vertical line
        let lineTop = (direction == "both" || direction == "up") ? topY : meanY
        let lineBottom = (direction == "both" || direction == "down") ? bottomY : meanY

        var vLine = Path()
        vLine.move(to: CGPoint(x: centerX, y: lineTop))
        vLine.addLine(to: CGPoint(x: centerX, y: lineBottom))
        context.stroke(vLine, with: .color(lineColor), lineWidth: thickness)

        // Draw caps
        if hasCap {
            if direction == "both" || direction == "up" {
                var topCap = Path()
                topCap.move(to: CGPoint(x: centerX - capWidth / 2, y: topY))
                topCap.addLine(to: CGPoint(x: centerX + capWidth / 2, y: topY))
                context.stroke(topCap, with: .color(lineColor), lineWidth: thickness)
            }

            if direction == "both" || direction == "down" {
                var bottomCap = Path()
                bottomCap.move(to: CGPoint(x: centerX - capWidth / 2, y: bottomY))
                bottomCap.addLine(to: CGPoint(x: centerX + capWidth / 2, y: bottomY))
                context.stroke(bottomCap, with: .color(lineColor), lineWidth: thickness)
            }
        }
    }

    // MARK: - Hit Regions

    /// Compute clickable regions for each bar, using the same position math as draw().
    public static func hitRegions(
        plotRect: CGRect,
        groups: [GroupData],
        style: StyleSpec
    ) -> [ChartHitRegion] {
        guard !groups.isEmpty else { return [] }

        let yRange = computeYRange(groups: groups, errorType: style.errorType)
        let groupWidth = plotRect.width / CGFloat(groups.count)
        let barFraction = CGFloat(style.barWidth)

        var regions: [ChartHitRegion] = []
        for (i, group) in groups.enumerated() {
            let centerX = plotRect.minX + (CGFloat(i) + 0.5) * groupWidth
            let barW = groupWidth * barFraction
            guard let mean = group.values.mean else { continue }

            let barTop = yToCanvas(mean, plotRect: plotRect, yRange: yRange)
            let barBottom = yToCanvas(max(yRange.min, 0), plotRect: plotRect, yRange: yRange)

            let rect = CGRect(
                x: centerX - barW / 2,
                y: min(barTop, barBottom),
                width: barW,
                height: abs(barBottom - barTop)
            )

            var meta: [String: String] = [
                "mean": String(format: "%.4f", mean),
                "n": "\(group.values.n)",
            ]
            if let sem = group.values.sem { meta["sem"] = String(format: "%.4f", sem) }
            if let sd = group.values.sd { meta["sd"] = String(format: "%.4f", sd) }

            regions.append(ChartHitRegion(
                kind: .bar,
                rect: rect,
                groupIndex: i,
                groupName: group.name,
                label: group.name,
                metadata: meta
            ))
        }
        return regions
    }

    // MARK: - Data points

    private static func drawDataPoints(
        in context: GraphicsContext,
        values: [Double],
        centerX: CGFloat,
        plotRect: CGRect,
        yRange: (min: Double, max: Double),
        color: Color,
        pointSize: CGFloat,
        alpha: Double,
        jitterWidth: CGFloat,
        shape: String = "circle",
        borderColor: Color = .black,
        borderThickness: CGFloat = 1.0
    ) {
        for (idx, val) in values.enumerated() {
            let jitter = jitterForIndex(idx, count: values.count, width: jitterWidth)
            let x = centerX + jitter
            let y = yToCanvas(val, plotRect: plotRect, yRange: yRange)

            let r = pointSize / 2
            let path: Path

            switch shape {
            case "square":
                path = Path(CGRect(x: x - r, y: y - r, width: pointSize, height: pointSize))
            case "diamond":
                var p = Path()
                p.move(to: CGPoint(x: x, y: y - r))
                p.addLine(to: CGPoint(x: x + r, y: y))
                p.addLine(to: CGPoint(x: x, y: y + r))
                p.addLine(to: CGPoint(x: x - r, y: y))
                p.closeSubpath()
                path = p
            case "triangle":
                var p = Path()
                p.move(to: CGPoint(x: x, y: y - r))
                p.addLine(to: CGPoint(x: x + r, y: y + r))
                p.addLine(to: CGPoint(x: x - r, y: y + r))
                p.closeSubpath()
                path = p
            case "plus":
                var p = Path()
                let t: CGFloat = 1.0
                p.addRect(CGRect(x: x - t/2, y: y - r, width: t, height: pointSize))
                p.addRect(CGRect(x: x - r, y: y - t/2, width: pointSize, height: t))
                path = p
            case "cross":
                var p = Path()
                p.move(to: CGPoint(x: x - r, y: y - r))
                p.addLine(to: CGPoint(x: x + r, y: y + r))
                p.move(to: CGPoint(x: x + r, y: y - r))
                p.addLine(to: CGPoint(x: x - r, y: y + r))
                path = p
            default: // circle
                path = Path(ellipseIn: CGRect(x: x - r, y: y - r, width: pointSize, height: pointSize))
            }

            if shape == "plus" || shape == "cross" {
                context.stroke(path, with: .color(color.opacity(alpha)), lineWidth: 1.5)
            } else {
                context.fill(path, with: .color(color.opacity(alpha)))
                context.stroke(path, with: .color(borderColor.opacity(min(alpha + 0.2, 1.0))),
                               lineWidth: borderThickness)
            }
        }
    }
}

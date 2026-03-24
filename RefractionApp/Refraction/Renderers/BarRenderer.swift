// BarRenderer.swift — Draws bar charts with error bars and jittered data
// points using SwiftUI Canvas + Core Graphics.

import SwiftUI

enum BarRenderer {

    /// Draw bars, error bars, and optional data points.
    static func draw(
        in context: GraphicsContext,
        plotRect: CGRect,
        groups: [GroupData],
        style: StyleSpec
    ) {
        guard !groups.isEmpty else { return }

        // Compute Y range from data
        let yRange = computeYRange(groups: groups, errorType: style.errorType)
        let groupWidth = plotRect.width / CGFloat(groups.count)
        let barFraction = CGFloat(style.barWidth)

        for (i, group) in groups.enumerated() {
            let color = Color(hex: colorForIndex(i, style: style))
            let centerX = plotRect.minX + (CGFloat(i) + 0.5) * groupWidth
            let barW = groupWidth * barFraction

            guard let mean = group.values.mean else { continue }

            // Map mean to canvas Y
            let barTop = yToCanvas(mean, plotRect: plotRect, yRange: yRange)
            let barBottom = yToCanvas(max(yRange.min, 0), plotRect: plotRect, yRange: yRange)

            // Draw bar
            let barRect = CGRect(
                x: centerX - barW / 2,
                y: min(barTop, barBottom),
                width: barW,
                height: abs(barBottom - barTop)
            )
            context.fill(Path(barRect), with: .color(color.opacity(0.85)))

            // Bar outline (darker shade)
            let darkColor = color.opacity(1.0)
            context.stroke(Path(barRect), with: .color(darkColor), lineWidth: 0.8)

            // Error bar
            let errorHalf = errorValue(for: group, errorType: style.errorType)
            if errorHalf > 0 {
                drawErrorBar(
                    in: context,
                    centerX: centerX,
                    mean: mean,
                    errorHalf: errorHalf,
                    plotRect: plotRect,
                    yRange: yRange,
                    capWidth: barW * 0.4
                )
            }

            // Jittered data points
            if style.showPoints {
                drawDataPoints(
                    in: context,
                    values: group.values.raw,
                    centerX: centerX,
                    plotRect: plotRect,
                    yRange: yRange,
                    color: color,
                    pointSize: CGFloat(style.pointSize),
                    alpha: style.pointAlpha,
                    jitterWidth: barW * 0.3
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
        capWidth: CGFloat
    ) {
        let top = yToCanvas(mean + errorHalf, plotRect: plotRect, yRange: yRange)
        let bottom = yToCanvas(mean - errorHalf, plotRect: plotRect, yRange: yRange)
        let lineColor = Color(hex: "#222222")

        // Vertical line
        var vLine = Path()
        vLine.move(to: CGPoint(x: centerX, y: top))
        vLine.addLine(to: CGPoint(x: centerX, y: bottom))
        context.stroke(vLine, with: .color(lineColor), lineWidth: 1.0)

        // Top cap
        var topCap = Path()
        topCap.move(to: CGPoint(x: centerX - capWidth / 2, y: top))
        topCap.addLine(to: CGPoint(x: centerX + capWidth / 2, y: top))
        context.stroke(topCap, with: .color(lineColor), lineWidth: 1.0)

        // Bottom cap
        var bottomCap = Path()
        bottomCap.move(to: CGPoint(x: centerX - capWidth / 2, y: bottom))
        bottomCap.addLine(to: CGPoint(x: centerX + capWidth / 2, y: bottom))
        context.stroke(bottomCap, with: .color(lineColor), lineWidth: 1.0)
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
        jitterWidth: CGFloat
    ) {
        // Deterministic jitter using value index as seed
        for (idx, val) in values.enumerated() {
            let jitter = jitterForIndex(idx, count: values.count, width: jitterWidth)
            let x = centerX + jitter
            let y = yToCanvas(val, plotRect: plotRect, yRange: yRange)

            let pointRect = CGRect(
                x: x - pointSize / 2,
                y: y - pointSize / 2,
                width: pointSize,
                height: pointSize
            )

            context.fill(
                Path(ellipseIn: pointRect),
                with: .color(color.opacity(alpha))
            )
            context.stroke(
                Path(ellipseIn: pointRect),
                with: .color(color.opacity(min(alpha + 0.2, 1.0))),
                lineWidth: 0.5
            )
        }
    }

    // MARK: - Coordinate mapping

    /// Map a data Y value to canvas Y coordinate.
    private static func yToCanvas(
        _ value: Double,
        plotRect: CGRect,
        yRange: (min: Double, max: Double)
    ) -> CGFloat {
        guard yRange.max > yRange.min else { return plotRect.midY }
        let fraction = (value - yRange.min) / (yRange.max - yRange.min)
        return plotRect.maxY - CGFloat(fraction) * plotRect.height
    }

    /// Compute the Y axis range from group data.
    private static func computeYRange(
        groups: [GroupData],
        errorType: String
    ) -> (min: Double, max: Double) {
        var allMax: Double = 0
        var allMin: Double = 0

        for g in groups {
            guard let mean = g.values.mean else { continue }
            let err = errorValue(for: g, errorType: errorType)
            allMax = Swift.max(allMax, mean + err)
            allMin = Swift.min(allMin, mean - err)

            // Also consider raw values
            for v in g.values.raw {
                allMax = Swift.max(allMax, v)
                allMin = Swift.min(allMin, v)
            }
        }

        let padding = (allMax - allMin) * 0.1
        return (min: Swift.min(allMin, 0), max: allMax + padding)
    }

    /// Get the error bar half-width for a group based on the error type.
    private static func errorValue(for group: GroupData, errorType: String) -> Double {
        switch errorType {
        case "sem": return group.values.sem ?? 0
        case "sd":  return group.values.sd ?? 0
        case "ci95": return group.values.ci95 ?? 0
        default: return group.values.sem ?? 0
        }
    }

    /// Deterministic jitter for point index.
    private static func jitterForIndex(_ index: Int, count: Int, width: CGFloat) -> CGFloat {
        guard count > 1 else { return 0 }
        // Spread points evenly with slight pseudo-random offset
        let base = CGFloat(index) / CGFloat(count - 1) - 0.5 // -0.5 to 0.5
        // Add a small deterministic perturbation based on index
        let hash = Double((index * 2654435761) & 0xFFFF) / 65535.0 - 0.5
        return (base * 0.6 + CGFloat(hash) * 0.4) * width
    }

    /// Get the color for a group index from the style spec.
    private static func colorForIndex(_ index: Int, style: StyleSpec) -> String {
        if index < style.colors.count {
            return style.colors[index]
        }
        return StyleSpec.defaultColors[index % StyleSpec.defaultColors.count]
    }
}

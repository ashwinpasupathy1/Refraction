// BracketRenderer.swift — Draws significance brackets between groups.
// Brackets show statistical comparison results (e.g. "***", "ns", "p=0.023")
// with data-aware stacking that places narrower brackets closer to the data
// and wider brackets above, similar to GraphPad Prism's algorithm.

import SwiftUI

public enum BracketRenderer {

    /// Vertical spacing between stacked brackets.
    private static let bracketSpacing: CGFloat = 20

    /// Padding above the tallest data element to the first bracket.
    private static let topPadding: CGFloat = 14

    /// Label offset above the horizontal bar.
    private static let labelOffset: CGFloat = 3

    // MARK: - Main draw

    /// Draw all significance brackets with smart stacking.
    public static func draw(
        in context: GraphicsContext,
        plotRect: CGRect,
        brackets: [Bracket],
        groupCount: Int,
        style: StyleSpec,
        groups: [GroupData] = []
    ) {
        guard groupCount > 0, !brackets.isEmpty else { return }

        let groupWidth = plotRect.width / CGFloat(groupCount)
        let bracketColor = resolveBracketColor(style)
        let lineWidth = CGFloat(style.bracketThickness)
        let capWidth = CGFloat(style.bracketCapWidth)

        // Compute the top Y of each group's data (bar top + error bar)
        let groupTops = computeGroupTops(
            groups: groups, plotRect: plotRect,
            yRange: computeYRange(groups: groups, errorType: style.errorType)
        )

        // Smart stacking: sort by span width (narrower first), then assign levels
        let sorted = smartStack(brackets: brackets, groupCount: groupCount)

        for (bracket, level) in sorted {
            let leftIndex = bracket.leftIndex
            let rightIndex = bracket.rightIndex

            guard leftIndex >= 0, leftIndex < groupCount,
                  rightIndex >= 0, rightIndex < groupCount else { continue }

            // X positions: center of each group
            let leftX = plotRect.minX + (CGFloat(leftIndex) + 0.5) * groupWidth
            let rightX = plotRect.minX + (CGFloat(rightIndex) + 0.5) * groupWidth

            // Y position: start above the tallest data in the spanned range,
            // then offset by the assigned level
            let spanMin = min(leftIndex, rightIndex)
            let spanMax = max(leftIndex, rightIndex)
            var highestTop = plotRect.minY  // default to top of plot
            if !groupTops.isEmpty {
                for gi in spanMin...spanMax {
                    if gi < groupTops.count {
                        highestTop = min(highestTop, groupTops[gi])
                    }
                }
            }

            let bracketY = highestTop - topPadding - CGFloat(level) * bracketSpacing

            // Draw based on style
            switch style.bracketStyle {
            case "uncapped":
                drawUncapped(in: context, leftX: leftX, rightX: rightX,
                             bracketY: bracketY, color: bracketColor, lineWidth: lineWidth)
            case "line":
                drawLine(in: context, leftX: leftX, rightX: rightX,
                         bracketY: bracketY, color: bracketColor, lineWidth: lineWidth)
            default: // "capped"
                drawCapped(in: context, leftX: leftX, rightX: rightX,
                           bracketY: bracketY, color: bracketColor,
                           lineWidth: lineWidth, capWidth: capWidth)
            }

            // Draw label
            let midX = (leftX + rightX) / 2
            let labelY = bracketY - labelOffset
            let labelString = formatLabel(bracket: bracket, style: style)

            let labelText = Text(labelString)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(bracketColor)
            context.draw(labelText, at: CGPoint(x: midX, y: labelY), anchor: .bottom)
        }
    }

    // MARK: - Hit Regions

    /// Generate hit regions for bracket interactivity.
    public static func hitRegions(
        plotRect: CGRect,
        brackets: [Bracket],
        groupCount: Int,
        style: StyleSpec,
        groups: [GroupData] = []
    ) -> [ChartHitRegion] {
        guard groupCount > 0, !brackets.isEmpty else { return [] }

        let groupWidth = plotRect.width / CGFloat(groupCount)
        let groupTops = computeGroupTops(
            groups: groups, plotRect: plotRect,
            yRange: computeYRange(groups: groups, errorType: style.errorType)
        )
        let sorted = smartStack(brackets: brackets, groupCount: groupCount)

        var regions: [ChartHitRegion] = []

        for (bracket, level) in sorted {
            let leftIndex = bracket.leftIndex
            let rightIndex = bracket.rightIndex
            guard leftIndex >= 0, leftIndex < groupCount,
                  rightIndex >= 0, rightIndex < groupCount else { continue }

            let leftX = plotRect.minX + (CGFloat(leftIndex) + 0.5) * groupWidth
            let rightX = plotRect.minX + (CGFloat(rightIndex) + 0.5) * groupWidth

            let spanMin = min(leftIndex, rightIndex)
            let spanMax = max(leftIndex, rightIndex)
            var highestTop = plotRect.minY
            if !groupTops.isEmpty {
                for gi in spanMin...spanMax {
                    if gi < groupTops.count {
                        highestTop = min(highestTop, groupTops[gi])
                    }
                }
            }

            let bracketY = highestTop - topPadding - CGFloat(level) * bracketSpacing

            // Hit region: rectangle around the bracket area
            let hitRect = CGRect(
                x: min(leftX, rightX) - 4,
                y: bracketY - 14,
                width: abs(rightX - leftX) + 8,
                height: bracketSpacing
            )

            var metadata: [String: String] = ["label": bracket.label]
            if let p = bracket.pValue {
                metadata["p_value"] = String(format: "%.4f", p)
            }

            regions.append(ChartHitRegion(
                kind: .bracket,
                rect: hitRect,
                groupIndex: leftIndex,
                groupName: "\(leftIndex)–\(rightIndex)",
                label: bracket.label,
                metadata: metadata
            ))
        }

        return regions
    }

    // MARK: - Smart Stacking

    /// Sort brackets by span width (narrower first) and assign non-overlapping levels.
    /// Returns an array of (bracket, level) pairs.
    private static func smartStack(
        brackets: [Bracket],
        groupCount: Int
    ) -> [(Bracket, Int)] {
        // Sort by span width (narrower brackets closer to data), then by left index
        let sorted = brackets.sorted { a, b in
            let spanA = abs(a.rightIndex - a.leftIndex)
            let spanB = abs(b.rightIndex - b.leftIndex)
            if spanA != spanB { return spanA < spanB }
            return a.leftIndex < b.leftIndex
        }

        // Greedy level assignment: for each bracket, find the lowest level
        // where it doesn't overlap with any already-placed bracket.
        // "Overlap" means their horizontal spans intersect.
        struct Placed {
            let spanMin: Int
            let spanMax: Int
            let level: Int
        }
        var placed: [Placed] = []
        var result: [(Bracket, Int)] = []

        for bracket in sorted {
            let spanMin = min(bracket.leftIndex, bracket.rightIndex)
            let spanMax = max(bracket.leftIndex, bracket.rightIndex)

            // Find the first level where this bracket doesn't overlap with
            // any already-placed bracket at the same level
            var level = 0
            var foundLevel = false
            while !foundLevel {
                let conflictsAtLevel = placed.filter { $0.level == level }
                let hasConflict = conflictsAtLevel.contains { p in
                    // Two spans overlap if one starts before the other ends
                    spanMin <= p.spanMax && spanMax >= p.spanMin
                }
                if !hasConflict {
                    foundLevel = true
                } else {
                    level += 1
                }
            }

            placed.append(Placed(spanMin: spanMin, spanMax: spanMax, level: level))
            result.append((bracket, level))
        }

        return result
    }

    // MARK: - Bracket Styles

    /// Capped bracket: vertical drops + horizontal bar (Prism default).
    private static func drawCapped(
        in context: GraphicsContext,
        leftX: CGFloat, rightX: CGFloat, bracketY: CGFloat,
        color: Color, lineWidth: CGFloat, capWidth: CGFloat
    ) {
        // Left vertical cap
        var leftDrop = Path()
        leftDrop.move(to: CGPoint(x: leftX, y: bracketY + capWidth))
        leftDrop.addLine(to: CGPoint(x: leftX, y: bracketY))
        context.stroke(leftDrop, with: .color(color), lineWidth: lineWidth)

        // Horizontal bar
        var hBar = Path()
        hBar.move(to: CGPoint(x: leftX, y: bracketY))
        hBar.addLine(to: CGPoint(x: rightX, y: bracketY))
        context.stroke(hBar, with: .color(color), lineWidth: lineWidth)

        // Right vertical cap
        var rightDrop = Path()
        rightDrop.move(to: CGPoint(x: rightX, y: bracketY))
        rightDrop.addLine(to: CGPoint(x: rightX, y: bracketY + capWidth))
        context.stroke(rightDrop, with: .color(color), lineWidth: lineWidth)
    }

    /// Uncapped bracket: horizontal bar only, no vertical drops.
    private static func drawUncapped(
        in context: GraphicsContext,
        leftX: CGFloat, rightX: CGFloat, bracketY: CGFloat,
        color: Color, lineWidth: CGFloat
    ) {
        var hBar = Path()
        hBar.move(to: CGPoint(x: leftX, y: bracketY))
        hBar.addLine(to: CGPoint(x: rightX, y: bracketY))
        context.stroke(hBar, with: .color(color), lineWidth: lineWidth)
    }

    /// Line style: thin line from left group top to right group top (no horizontal bar).
    private static func drawLine(
        in context: GraphicsContext,
        leftX: CGFloat, rightX: CGFloat, bracketY: CGFloat,
        color: Color, lineWidth: CGFloat
    ) {
        var path = Path()
        path.move(to: CGPoint(x: leftX, y: bracketY))
        path.addLine(to: CGPoint(x: rightX, y: bracketY))
        context.stroke(path, with: .color(color),
                       style: StrokeStyle(lineWidth: lineWidth, dash: [4, 3]))
    }

    // MARK: - Label Formatting

    /// Format the bracket label based on style settings.
    private static func formatLabel(bracket: Bracket, style: StyleSpec) -> String {
        switch style.bracketLabelStyle {
        case "p_value":
            if let p = bracket.pValue {
                if p < 0.0001 { return "p<0.0001" }
                return "p=\(String(format: "%.4f", p))"
            }
            return bracket.label

        case "both":
            var parts = [bracket.label]
            if let p = bracket.pValue {
                if p < 0.0001 {
                    parts.append("(p<0.0001)")
                } else {
                    parts.append("(p=\(String(format: "%.3f", p)))")
                }
            }
            return parts.joined(separator: " ")

        default: // "stars"
            return bracket.label
        }
    }

    // MARK: - Data-Aware Positioning

    /// Compute the canvas Y coordinate of the top of each group's data
    /// (mean + error bar, or max raw point — whichever is higher).
    private static func computeGroupTops(
        groups: [GroupData],
        plotRect: CGRect,
        yRange: (min: Double, max: Double)
    ) -> [CGFloat] {
        guard !groups.isEmpty, yRange.max > yRange.min else {
            return Array(repeating: plotRect.minY, count: groups.count)
        }

        return groups.map { group in
            var topValue = 0.0

            if let mean = group.values.mean {
                let err: Double
                if let sem = group.values.sem { err = sem }
                else if let sd = group.values.sd { err = sd }
                else { err = 0 }
                topValue = mean + err
            }

            // Also check raw points
            for v in group.values.raw {
                topValue = max(topValue, v)
            }

            return yToCanvas(topValue, plotRect: plotRect, yRange: yRange)
        }
    }

    /// Resolve bracket color from style, defaulting to dark gray.
    private static func resolveBracketColor(_ style: StyleSpec) -> Color {
        let hex = style.bracketColor
        if hex == "auto" || hex.isEmpty { return Color(hex: "#222222") }
        return Color(hex: hex)
    }
}

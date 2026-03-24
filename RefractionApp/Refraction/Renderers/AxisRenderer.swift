// AxisRenderer.swift — Draws Prism-style open spines, tick marks,
// axis labels, and chart title using SwiftUI Canvas + Core Graphics.

import SwiftUI

enum AxisRenderer {

    /// Draw axes (spines, ticks, labels, title) into the canvas context.
    static func draw(
        in context: GraphicsContext,
        plotRect: CGRect,
        canvasSize: CGSize,
        spec: AxisSpec,
        style: StyleSpec,
        groups: [String]
    ) {
        let spineColor = Color(hex: "#222222")
        let lineWidth = spec.spineWidth

        // MARK: - Spines

        switch style.axisStyle {
        case "open":
            // Left spine (Y axis)
            drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.topLeft,
                     color: spineColor, width: lineWidth)
            // Bottom spine (X axis)
            drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.bottomRight,
                     color: spineColor, width: lineWidth)

        case "closed":
            // All four spines
            drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.topLeft,
                     color: spineColor, width: lineWidth)
            drawLine(in: context, from: plotRect.bottomLeft, to: plotRect.bottomRight,
                     color: spineColor, width: lineWidth)
            drawLine(in: context, from: plotRect.topLeft, to: plotRect.topRight,
                     color: spineColor, width: lineWidth)
            drawLine(in: context, from: plotRect.bottomRight, to: plotRect.topRight,
                     color: spineColor, width: lineWidth)

        case "floating":
            // Left and bottom, offset slightly from the plot area
            let offset: CGFloat = 4
            drawLine(in: context,
                     from: CGPoint(x: plotRect.minX - offset, y: plotRect.maxY + offset),
                     to: CGPoint(x: plotRect.minX - offset, y: plotRect.minY),
                     color: spineColor, width: lineWidth)
            drawLine(in: context,
                     from: CGPoint(x: plotRect.minX - offset, y: plotRect.maxY + offset),
                     to: CGPoint(x: plotRect.maxX, y: plotRect.maxY + offset),
                     color: spineColor, width: lineWidth)

        default: // "none"
            break
        }

        // MARK: - Y-axis ticks

        let nYTicks = 5
        let fontSize = CGFloat(spec.fontSize)
        let tickLen: CGFloat = 5

        for i in 0...nYTicks {
            let fraction = CGFloat(i) / CGFloat(nYTicks)
            let y = plotRect.maxY - fraction * plotRect.height

            // Tick mark
            let tickStart: CGPoint
            let tickEnd: CGPoint

            switch spec.tickDirection {
            case "out":
                tickStart = CGPoint(x: plotRect.minX, y: y)
                tickEnd = CGPoint(x: plotRect.minX - tickLen, y: y)
            case "in":
                tickStart = CGPoint(x: plotRect.minX, y: y)
                tickEnd = CGPoint(x: plotRect.minX + tickLen, y: y)
            case "inout":
                tickStart = CGPoint(x: plotRect.minX - tickLen / 2, y: y)
                tickEnd = CGPoint(x: plotRect.minX + tickLen / 2, y: y)
            default:
                continue
            }

            drawLine(in: context, from: tickStart, to: tickEnd,
                     color: spineColor, width: 0.8)
        }

        // MARK: - X-axis category labels

        if !groups.isEmpty {
            let groupWidth = plotRect.width / CGFloat(groups.count)

            for (i, name) in groups.enumerated() {
                let x = plotRect.minX + (CGFloat(i) + 0.5) * groupWidth
                let y = plotRect.maxY

                // Tick mark
                if !spec.tickDirection.isEmpty {
                    let tickY: CGFloat
                    switch spec.tickDirection {
                    case "out":  tickY = y + tickLen
                    case "in":   tickY = y - tickLen
                    default:     tickY = y + tickLen
                    }
                    drawLine(in: context,
                             from: CGPoint(x: x, y: y),
                             to: CGPoint(x: x, y: tickY),
                             color: spineColor, width: 0.8)
                }

                // Label
                let label = Text(name)
                    .font(.system(size: fontSize - 1))
                    .foregroundStyle(Color(hex: "#222222"))
                context.draw(label, at: CGPoint(x: x, y: y + tickLen + 12), anchor: .top)
            }
        }

        // MARK: - Axis labels

        if !spec.xLabel.isEmpty {
            let xLabelText = Text(spec.xLabel)
                .font(.system(size: fontSize))
                .foregroundStyle(Color(hex: "#222222"))
            context.draw(
                xLabelText,
                at: CGPoint(x: plotRect.midX, y: canvasSize.height - 8),
                anchor: .bottom
            )
        }

        if !spec.yLabel.isEmpty {
            // Rotate for Y-axis label
            var yContext = context
            let yLabelPos = CGPoint(x: 14, y: plotRect.midY)
            yContext.translateBy(x: yLabelPos.x, y: yLabelPos.y)
            yContext.rotate(by: .degrees(-90))

            let yLabelText = Text(spec.yLabel)
                .font(.system(size: fontSize))
                .foregroundStyle(Color(hex: "#222222"))
            yContext.draw(yLabelText, at: .zero, anchor: .center)
        }

        // MARK: - Title

        if !spec.title.isEmpty {
            let titleText = Text(spec.title)
                .font(.system(size: fontSize + 2, weight: .semibold))
                .foregroundStyle(Color(hex: "#222222"))
            context.draw(titleText, at: CGPoint(x: plotRect.midX, y: 16), anchor: .top)
        }
    }

    // MARK: - Helpers

    private static func drawLine(
        in context: GraphicsContext,
        from: CGPoint, to: CGPoint,
        color: Color, width: CGFloat
    ) {
        var path = Path()
        path.move(to: from)
        path.addLine(to: to)
        context.stroke(path, with: .color(color), lineWidth: width)
    }
}

// MARK: - CGRect convenience

private extension CGRect {
    var topLeft: CGPoint { CGPoint(x: minX, y: minY) }
    var topRight: CGPoint { CGPoint(x: maxX, y: minY) }
    var bottomLeft: CGPoint { CGPoint(x: minX, y: maxY) }
    var bottomRight: CGPoint { CGPoint(x: maxX, y: maxY) }
}

// MARK: - Color from hex string

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255.0
        let g = Double((int >> 8) & 0xFF) / 255.0
        let b = Double(int & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}

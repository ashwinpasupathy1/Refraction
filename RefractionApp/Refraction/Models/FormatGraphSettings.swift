// FormatGraphSettings.swift — Renderer-only visual overrides for a graph sheet.
// These settings are applied by the SwiftUI renderer on top of the ChartSpec data.
// Nothing here triggers an engine call — it's purely visual formatting.

import Foundation
import SwiftUI

@Observable
final class FormatGraphSettings: Codable {

    // MARK: - Symbols (data points)

    var showSymbols: Bool = true
    var symbolColor: String = "#000000"
    var symbolShape: SymbolShape = .circle
    var symbolSize: Double = 6.0
    var symbolBorderColor: String = "#000000"
    var symbolBorderThickness: Double = 1.0

    // MARK: - Bars

    var showBars: Bool = true
    var barColor: String = "#000000"    // "auto" = use group color
    var barWidth: Double = 0.6
    var barFillOpacity: Double = 0.85
    var barBorderColor: String = "#000000"
    var barBorderThickness: Double = 0.8
    var barPattern: BarPattern = .solid
    var barsBeginAtY: Double = 0.0

    // MARK: - Error bars

    var showErrorBars: Bool = true
    var errorBarColor: String = "#222222"
    var errorBarDirection: ErrorBarDirection = .both
    var errorBarStyle: ErrorBarStyle = .tCap
    var errorBarThickness: Double = 1.0

    // MARK: - Connecting line

    var showConnectingLine: Bool = false
    var lineColor: String = "#000000"
    var lineThickness: Double = 1.5
    var lineStyle: LineStyle = .solid
    var connectMeans: Bool = true
    var startAtOrigin: Bool = false

    // MARK: - Area fill

    var showAreaFill: Bool = false
    var areaFillColor: String = "#000000"
    var areaFillPosition: AreaFillPosition = .below
    var areaFillAlpha: Double = 0.2

    // MARK: - Legend

    var showLegend: Bool = true

    // MARK: - Labels

    var labelPoints: Bool = false

    // MARK: - Enums

    enum SymbolShape: String, Codable, CaseIterable, Identifiable {
        case circle
        case square
        case triangle
        case diamond
        case plus
        case cross

        var id: String { rawValue }

        var label: String {
            switch self {
            case .circle:   return "Circle"
            case .square:   return "Square"
            case .triangle: return "Triangle"
            case .diamond:  return "Diamond"
            case .plus:     return "Plus"
            case .cross:    return "Cross"
            }
        }
    }

    enum BarPattern: String, Codable, CaseIterable, Identifiable {
        case solid
        case striped
        case dotted

        var id: String { rawValue }
        var label: String { rawValue.capitalized }
    }

    enum ErrorBarDirection: String, Codable, CaseIterable, Identifiable {
        case both
        case up
        case down

        var id: String { rawValue }
        var label: String { rawValue.capitalized }
    }

    enum ErrorBarStyle: String, Codable, CaseIterable, Identifiable {
        case tCap = "t_cap"
        case line

        var id: String { rawValue }

        var label: String {
            switch self {
            case .tCap: return "T-Cap"
            case .line:  return "Line"
            }
        }
    }

    enum LineStyle: String, Codable, CaseIterable, Identifiable {
        case solid
        case dashed
        case dotted

        var id: String { rawValue }
        var label: String { rawValue.capitalized }
    }

    enum AreaFillPosition: String, Codable, CaseIterable, Identifiable {
        case below
        case above

        var id: String { rawValue }
        var label: String { rawValue.capitalized }
    }

    // MARK: - Codable

    enum CodingKeys: String, CodingKey {
        case showSymbols, symbolColor, symbolShape, symbolSize
        case symbolBorderColor, symbolBorderThickness
        case showBars, barColor, barWidth, barBorderColor
        case barBorderThickness, barPattern, barsBeginAtY
        case showErrorBars, errorBarColor, errorBarDirection
        case errorBarStyle, errorBarThickness
        case showConnectingLine, lineColor, lineThickness
        case lineStyle, connectMeans, startAtOrigin
        case showAreaFill, areaFillColor, areaFillPosition, areaFillAlpha
        case showLegend, labelPoints
    }

    init() {}

    required init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        showSymbols = (try? c.decode(Bool.self, forKey: .showSymbols)) ?? true
        symbolColor = (try? c.decode(String.self, forKey: .symbolColor)) ?? "#000000"
        symbolShape = (try? c.decode(SymbolShape.self, forKey: .symbolShape)) ?? .circle
        symbolSize = (try? c.decode(Double.self, forKey: .symbolSize)) ?? 6.0
        symbolBorderColor = (try? c.decode(String.self, forKey: .symbolBorderColor)) ?? "#000000"
        symbolBorderThickness = (try? c.decode(Double.self, forKey: .symbolBorderThickness)) ?? 1.0
        showBars = (try? c.decode(Bool.self, forKey: .showBars)) ?? true
        barColor = (try? c.decode(String.self, forKey: .barColor)) ?? "#000000"
        barWidth = (try? c.decode(Double.self, forKey: .barWidth)) ?? 0.6
        barBorderColor = (try? c.decode(String.self, forKey: .barBorderColor)) ?? "#000000"
        barBorderThickness = (try? c.decode(Double.self, forKey: .barBorderThickness)) ?? 0.8
        barPattern = (try? c.decode(BarPattern.self, forKey: .barPattern)) ?? .solid
        barsBeginAtY = (try? c.decode(Double.self, forKey: .barsBeginAtY)) ?? 0.0
        showErrorBars = (try? c.decode(Bool.self, forKey: .showErrorBars)) ?? true
        errorBarColor = (try? c.decode(String.self, forKey: .errorBarColor)) ?? "#222222"
        errorBarDirection = (try? c.decode(ErrorBarDirection.self, forKey: .errorBarDirection)) ?? .both
        errorBarStyle = (try? c.decode(ErrorBarStyle.self, forKey: .errorBarStyle)) ?? .tCap
        errorBarThickness = (try? c.decode(Double.self, forKey: .errorBarThickness)) ?? 1.0
        showConnectingLine = (try? c.decode(Bool.self, forKey: .showConnectingLine)) ?? false
        lineColor = (try? c.decode(String.self, forKey: .lineColor)) ?? "#000000"
        lineThickness = (try? c.decode(Double.self, forKey: .lineThickness)) ?? 1.5
        lineStyle = (try? c.decode(LineStyle.self, forKey: .lineStyle)) ?? .solid
        connectMeans = (try? c.decode(Bool.self, forKey: .connectMeans)) ?? true
        startAtOrigin = (try? c.decode(Bool.self, forKey: .startAtOrigin)) ?? false
        showAreaFill = (try? c.decode(Bool.self, forKey: .showAreaFill)) ?? false
        areaFillColor = (try? c.decode(String.self, forKey: .areaFillColor)) ?? "#000000"
        areaFillPosition = (try? c.decode(AreaFillPosition.self, forKey: .areaFillPosition)) ?? .below
        areaFillAlpha = (try? c.decode(Double.self, forKey: .areaFillAlpha)) ?? 0.2
        showLegend = (try? c.decode(Bool.self, forKey: .showLegend)) ?? true
        labelPoints = (try? c.decode(Bool.self, forKey: .labelPoints)) ?? false
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(showSymbols, forKey: .showSymbols)
        try c.encode(symbolColor, forKey: .symbolColor)
        try c.encode(symbolShape, forKey: .symbolShape)
        try c.encode(symbolSize, forKey: .symbolSize)
        try c.encode(symbolBorderColor, forKey: .symbolBorderColor)
        try c.encode(symbolBorderThickness, forKey: .symbolBorderThickness)
        try c.encode(showBars, forKey: .showBars)
        try c.encode(barColor, forKey: .barColor)
        try c.encode(barWidth, forKey: .barWidth)
        try c.encode(barBorderColor, forKey: .barBorderColor)
        try c.encode(barBorderThickness, forKey: .barBorderThickness)
        try c.encode(barPattern, forKey: .barPattern)
        try c.encode(barsBeginAtY, forKey: .barsBeginAtY)
        try c.encode(showErrorBars, forKey: .showErrorBars)
        try c.encode(errorBarColor, forKey: .errorBarColor)
        try c.encode(errorBarDirection, forKey: .errorBarDirection)
        try c.encode(errorBarStyle, forKey: .errorBarStyle)
        try c.encode(errorBarThickness, forKey: .errorBarThickness)
        try c.encode(showConnectingLine, forKey: .showConnectingLine)
        try c.encode(lineColor, forKey: .lineColor)
        try c.encode(lineThickness, forKey: .lineThickness)
        try c.encode(lineStyle, forKey: .lineStyle)
        try c.encode(connectMeans, forKey: .connectMeans)
        try c.encode(startAtOrigin, forKey: .startAtOrigin)
        try c.encode(showAreaFill, forKey: .showAreaFill)
        try c.encode(areaFillColor, forKey: .areaFillColor)
        try c.encode(areaFillPosition, forKey: .areaFillPosition)
        try c.encode(areaFillAlpha, forKey: .areaFillAlpha)
        try c.encode(showLegend, forKey: .showLegend)
        try c.encode(labelPoints, forKey: .labelPoints)
    }
}

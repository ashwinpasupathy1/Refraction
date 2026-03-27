// ChartSpec.swift — Public decodable structs matching the Python analysis engine's
// renderer-independent ChartSpec JSON schema.
//
// Extracted from RefractionApp into the RefractionRenderer Swift Package
// so that renderers can be built and tested independently of the app shell.

import Foundation

// MARK: - Top-level response wrapper

/// The JSON envelope returned by POST /render.
public struct RenderResponse: Decodable {
    public let ok: Bool
    public let spec: ChartSpec?
    public let error: String?
}

// MARK: - ChartSpec (renderer-independent)

/// Top-level chart specification decoded from the Python analysis engine.
/// Maps Plotly's `{ data: [...], layout: {...} }` structure into a form
/// suitable for native Core Graphics rendering.
public struct ChartSpec: Decodable {
    public let chartType: String
    public let groups: [GroupData]
    public let style: StyleSpec
    public let axes: AxisSpec
    public let stats: StatsResult?
    public let brackets: [Bracket]
    public let referenceLine: ReferenceLine?
    /// Chart-type-specific data payload from dedicated analyzers.
    public let data: [String: JSONValue]?

    enum CodingKeys: String, CodingKey {
        case chartType = "chart_type"
        case groups, style, axes, stats, brackets, data
        case referenceLine = "reference_line"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        chartType = (try? container.decode(String.self, forKey: .chartType)) ?? "bar"
        groups = (try? container.decode([GroupData].self, forKey: .groups)) ?? []
        style = (try? container.decode(StyleSpec.self, forKey: .style)) ?? StyleSpec()
        axes = (try? container.decode(AxisSpec.self, forKey: .axes)) ?? AxisSpec()
        stats = try? container.decode(StatsResult.self, forKey: .stats)
        brackets = (try? container.decode([Bracket].self, forKey: .brackets)) ?? []
        referenceLine = try? container.decode(ReferenceLine.self, forKey: .referenceLine)
        data = try? container.decode([String: JSONValue].self, forKey: .data)
    }

    /// Memberwise initializer for programmatic construction.
    public init(
        chartType: String = "bar",
        groups: [GroupData] = [],
        style: StyleSpec = StyleSpec(),
        axes: AxisSpec = AxisSpec(),
        stats: StatsResult? = nil,
        brackets: [Bracket] = [],
        referenceLine: ReferenceLine? = nil,
        data: [String: JSONValue]? = nil
    ) {
        self.chartType = chartType
        self.groups = groups
        self.style = style
        self.axes = axes
        self.stats = stats
        self.brackets = brackets
        self.referenceLine = referenceLine
        self.data = data
    }
}

// MARK: - Group and Values

/// One data group (e.g. one bar, one box, one series).
public struct GroupData: Decodable, Identifiable {
    public var id: String { name }
    public let name: String
    public let values: ValuesData
    public let color: String

    public init(name: String, values: ValuesData, color: String) {
        self.name = name
        self.values = values
        self.color = color
    }

    enum CodingKeys: String, CodingKey {
        case name, values, color
    }
}

/// Numeric values for a single group — raw data plus precomputed summary stats.
public struct ValuesData: Decodable {
    public let raw: [Double]
    public let mean: Double?
    public let sem: Double?
    public let sd: Double?
    public let ci95: Double?
    public let n: Int

    public init(raw: [Double] = [], mean: Double? = nil, sem: Double? = nil,
         sd: Double? = nil, ci95: Double? = nil, n: Int = 0) {
        self.raw = raw
        self.mean = mean
        self.sem = sem
        self.sd = sd
        self.ci95 = ci95
        self.n = n
    }
}

// MARK: - Statistics

/// Result of statistical analysis performed by the Python engine.
public struct StatsResult: Decodable {
    public let testName: String
    public let pValue: Double?
    public let statistic: Double?
    public let comparisons: [Comparison]
    public let normality: NormalityResult?
    public let effectSize: Double?
    public let warning: String?

    enum CodingKeys: String, CodingKey {
        case testName = "test_name"
        case pValue = "p_value"
        case statistic
        case comparisons
        case normality
        case effectSize = "effect_size"
        case warning
    }
}

/// A single pairwise comparison (e.g. post-hoc test result).
public struct Comparison: Decodable {
    public let group1: String
    public let group2: String
    public let pValue: Double
    public let significant: Bool
    public let label: String

    enum CodingKeys: String, CodingKey {
        case group1 = "group_1"
        case group2 = "group_2"
        case pValue = "p_value"
        case significant, label
    }
}

/// Normality test results for the dataset.
public struct NormalityResult: Decodable {
    public let testName: String
    public let pValue: Double
    public let isNormal: Bool
    public let warning: String?

    enum CodingKeys: String, CodingKey {
        case testName = "test_name"
        case pValue = "p_value"
        case isNormal = "is_normal"
        case warning
    }
}

/// A significance bracket drawn between two groups.
public struct Bracket: Decodable {
    public let leftIndex: Int
    public let rightIndex: Int
    public let label: String
    public let stackingOrder: Int

    enum CodingKeys: String, CodingKey {
        case leftIndex = "left_index"
        case rightIndex = "right_index"
        case label
        case stackingOrder = "stacking_order"
    }
}

/// Horizontal reference line.
public struct ReferenceLine: Decodable {
    public let y: Double
    public let label: String
}

// MARK: - Style

/// Visual style parameters for the chart.
public struct StyleSpec: Decodable {
    public let colors: [String]
    public let showPoints: Bool
    public let showBrackets: Bool
    public let pointSize: Double
    public let pointAlpha: Double
    public let barWidth: Double
    public let errorType: String
    public let axisStyle: String

    // Format graph overrides (applied by FormatSettingsMerger)
    public let symbolShape: String
    public let symbolColor: String       // "auto" = use group color
    public let symbolBorderColor: String
    public let symbolBorderThickness: Double
    public let showBars: Bool
    public let barFillOpacity: Double
    public let barBorderColor: String
    public let barBorderThickness: Double
    public let errorBarColor: String
    public let errorBarDirection: String  // "both", "up", "down"
    public let errorBarStyle: String      // "t_cap", "line"
    public let errorBarThickness: Double
    public let showConnectingLine: Bool
    public let lineColor: String         // "auto" = use group color
    public let lineThickness: Double
    public let lineStyle: String         // "solid", "dashed", "dotted"
    public let showAreaFill: Bool
    public let areaFillColor: String
    public let areaFillPosition: String  // "below", "above"
    public let areaFillAlpha: Double
    public let showLegend: Bool

    public static let defaultColors = [
        "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
        "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
    ]

    public init(
        colors: [String] = defaultColors,
        showPoints: Bool = false,
        showBrackets: Bool = true,
        pointSize: Double = 6.0,
        pointAlpha: Double = 0.8,
        barWidth: Double = 0.6,
        errorType: String = "sem",
        axisStyle: String = "open",
        symbolShape: String = "circle",
        symbolColor: String = "auto",
        symbolBorderColor: String = "#000000",
        symbolBorderThickness: Double = 1.0,
        showBars: Bool = true,
        barFillOpacity: Double = 0.85,
        barBorderColor: String = "#000000",
        barBorderThickness: Double = 0.8,
        errorBarColor: String = "#222222",
        errorBarDirection: String = "both",
        errorBarStyle: String = "t_cap",
        errorBarThickness: Double = 1.0,
        showConnectingLine: Bool = false,
        lineColor: String = "auto",
        lineThickness: Double = 1.5,
        lineStyle: String = "solid",
        showAreaFill: Bool = false,
        areaFillColor: String = "#000000",
        areaFillPosition: String = "below",
        areaFillAlpha: Double = 0.2,
        showLegend: Bool = true
    ) {
        self.colors = colors
        self.showPoints = showPoints
        self.showBrackets = showBrackets
        self.pointSize = pointSize
        self.pointAlpha = pointAlpha
        self.barWidth = barWidth
        self.errorType = errorType
        self.axisStyle = axisStyle
        self.symbolShape = symbolShape
        self.symbolColor = symbolColor
        self.symbolBorderColor = symbolBorderColor
        self.symbolBorderThickness = symbolBorderThickness
        self.showBars = showBars
        self.barFillOpacity = barFillOpacity
        self.barBorderColor = barBorderColor
        self.barBorderThickness = barBorderThickness
        self.errorBarColor = errorBarColor
        self.errorBarDirection = errorBarDirection
        self.errorBarStyle = errorBarStyle
        self.errorBarThickness = errorBarThickness
        self.showConnectingLine = showConnectingLine
        self.lineColor = lineColor
        self.lineThickness = lineThickness
        self.lineStyle = lineStyle
        self.showAreaFill = showAreaFill
        self.areaFillColor = areaFillColor
        self.areaFillPosition = areaFillPosition
        self.areaFillAlpha = areaFillAlpha
        self.showLegend = showLegend
    }

    enum CodingKeys: String, CodingKey {
        case colors
        case showPoints = "show_points"
        case showBrackets = "show_brackets"
        case pointSize = "point_size"
        case pointAlpha = "point_alpha"
        case barWidth = "bar_width"
        case errorType = "error_type"
        case axisStyle = "axis_style"
        case symbolShape = "symbol_shape"
        case symbolColor = "symbol_color"
        case symbolBorderColor = "symbol_border_color"
        case symbolBorderThickness = "symbol_border_thickness"
        case showBars = "show_bars"
        case barFillOpacity = "bar_fill_opacity"
        case barBorderColor = "bar_border_color"
        case barBorderThickness = "bar_border_thickness"
        case errorBarColor = "error_bar_color"
        case errorBarDirection = "error_bar_direction"
        case errorBarStyle = "error_bar_style"
        case errorBarThickness = "error_bar_thickness"
        case showConnectingLine = "show_connecting_line"
        case lineColor = "line_color"
        case lineThickness = "line_thickness"
        case lineStyle = "line_style"
        case showAreaFill = "show_area_fill"
        case areaFillColor = "area_fill_color"
        case areaFillPosition = "area_fill_position"
        case areaFillAlpha = "area_fill_alpha"
        case showLegend = "show_legend"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        colors = (try? c.decode([String].self, forKey: .colors)) ?? StyleSpec.defaultColors
        showPoints = (try? c.decode(Bool.self, forKey: .showPoints)) ?? false
        showBrackets = (try? c.decode(Bool.self, forKey: .showBrackets)) ?? true
        pointSize = (try? c.decode(Double.self, forKey: .pointSize)) ?? 6.0
        pointAlpha = (try? c.decode(Double.self, forKey: .pointAlpha)) ?? 0.8
        barWidth = (try? c.decode(Double.self, forKey: .barWidth)) ?? 0.6
        errorType = (try? c.decode(String.self, forKey: .errorType)) ?? "sem"
        axisStyle = (try? c.decode(String.self, forKey: .axisStyle)) ?? "open"
        symbolShape = (try? c.decode(String.self, forKey: .symbolShape)) ?? "circle"
        symbolColor = (try? c.decode(String.self, forKey: .symbolColor)) ?? "auto"
        symbolBorderColor = (try? c.decode(String.self, forKey: .symbolBorderColor)) ?? "#000000"
        symbolBorderThickness = (try? c.decode(Double.self, forKey: .symbolBorderThickness)) ?? 1.0
        showBars = (try? c.decode(Bool.self, forKey: .showBars)) ?? true
        barFillOpacity = (try? c.decode(Double.self, forKey: .barFillOpacity)) ?? 0.85
        barBorderColor = (try? c.decode(String.self, forKey: .barBorderColor)) ?? "#000000"
        barBorderThickness = (try? c.decode(Double.self, forKey: .barBorderThickness)) ?? 0.8
        errorBarColor = (try? c.decode(String.self, forKey: .errorBarColor)) ?? "#222222"
        errorBarDirection = (try? c.decode(String.self, forKey: .errorBarDirection)) ?? "both"
        errorBarStyle = (try? c.decode(String.self, forKey: .errorBarStyle)) ?? "t_cap"
        errorBarThickness = (try? c.decode(Double.self, forKey: .errorBarThickness)) ?? 1.0
        showConnectingLine = (try? c.decode(Bool.self, forKey: .showConnectingLine)) ?? false
        lineColor = (try? c.decode(String.self, forKey: .lineColor)) ?? "auto"
        lineThickness = (try? c.decode(Double.self, forKey: .lineThickness)) ?? 1.5
        lineStyle = (try? c.decode(String.self, forKey: .lineStyle)) ?? "solid"
        showAreaFill = (try? c.decode(Bool.self, forKey: .showAreaFill)) ?? false
        areaFillColor = (try? c.decode(String.self, forKey: .areaFillColor)) ?? "#000000"
        areaFillPosition = (try? c.decode(String.self, forKey: .areaFillPosition)) ?? "below"
        areaFillAlpha = (try? c.decode(Double.self, forKey: .areaFillAlpha)) ?? 0.2
        showLegend = (try? c.decode(Bool.self, forKey: .showLegend)) ?? true
    }
}

// MARK: - Axes

/// Axis configuration with precomputed tick positions from the engine.
public struct AxisSpec: Decodable {
    public let title: String
    public let xLabel: String
    public let yLabel: String
    public let xScale: String
    public let yScale: String
    public let xRange: [Double]?
    public let yRange: [Double]?
    public let yTicks: [Double]         // precomputed Y tick positions
    public let yTickLabels: [String]    // formatted tick labels
    public let tickDirection: String
    public let spineWidth: Double
    public let fontSize: Double

    // Format axes overrides (applied by FormatSettingsMerger)
    public let axisColor: String
    public let xTickDirection: String
    public let xTickLength: Double
    public let yTickLength: Double
    public let titleFontSize: Double
    public let xLabelFontSize: Double
    public let yLabelFontSize: Double
    public let xTickLabelFontSize: Double
    public let yTickLabelFontSize: Double
    public let xLabelRotation: Double
    public let hideAxes: String          // "show_both", "hide_x", "hide_y", "hide_both"
    public let majorGrid: String         // "none", "solid", "dashed", "dotted"
    public let majorGridColor: String
    public let majorGridThickness: Double
    public let minorGrid: String
    public let minorGridColor: String
    public let minorGridThickness: Double
    public let plotAreaColor: String
    public let pageBackground: String
    public let globalFontName: String

    public init(
        title: String = "",
        xLabel: String = "",
        yLabel: String = "",
        xScale: String = "linear",
        yScale: String = "linear",
        xRange: [Double]? = nil,
        yRange: [Double]? = nil,
        yTicks: [Double] = [],
        yTickLabels: [String] = [],
        tickDirection: String = "out",
        spineWidth: Double = 1.0,
        fontSize: Double = 12.0,
        axisColor: String = "#222222",
        xTickDirection: String = "out",
        xTickLength: Double = 5.0,
        yTickLength: Double = 5.0,
        titleFontSize: Double = 14.0,
        xLabelFontSize: Double = 12.0,
        yLabelFontSize: Double = 12.0,
        xTickLabelFontSize: Double = 10.0,
        yTickLabelFontSize: Double = 10.0,
        xLabelRotation: Double = 0.0,
        hideAxes: String = "show_both",
        majorGrid: String = "none",
        majorGridColor: String = "#CCCCCC",
        majorGridThickness: Double = 1.0,
        minorGrid: String = "none",
        minorGridColor: String = "#EEEEEE",
        minorGridThickness: Double = 0.5,
        plotAreaColor: String = "clear",
        pageBackground: String = "clear",
        globalFontName: String = "Helvetica"
    ) {
        self.title = title
        self.xLabel = xLabel
        self.yLabel = yLabel
        self.xScale = xScale
        self.yScale = yScale
        self.xRange = xRange
        self.yRange = yRange
        self.yTicks = yTicks
        self.yTickLabels = yTickLabels
        self.tickDirection = tickDirection
        self.spineWidth = spineWidth
        self.fontSize = fontSize
        self.axisColor = axisColor
        self.xTickDirection = xTickDirection
        self.xTickLength = xTickLength
        self.yTickLength = yTickLength
        self.titleFontSize = titleFontSize
        self.xLabelFontSize = xLabelFontSize
        self.yLabelFontSize = yLabelFontSize
        self.xTickLabelFontSize = xTickLabelFontSize
        self.yTickLabelFontSize = yTickLabelFontSize
        self.xLabelRotation = xLabelRotation
        self.hideAxes = hideAxes
        self.majorGrid = majorGrid
        self.majorGridColor = majorGridColor
        self.majorGridThickness = majorGridThickness
        self.minorGrid = minorGrid
        self.minorGridColor = minorGridColor
        self.minorGridThickness = minorGridThickness
        self.plotAreaColor = plotAreaColor
        self.pageBackground = pageBackground
        self.globalFontName = globalFontName
    }

    enum CodingKeys: String, CodingKey {
        case title
        case xLabel = "x_label"
        case yLabel = "y_label"
        case xScale = "x_scale"
        case yScale = "y_scale"
        case xRange = "x_range"
        case yRange = "y_range"
        case yTicks = "y_ticks"
        case yTickLabels = "y_tick_labels"
        case tickDirection = "tick_direction"
        case spineWidth = "spine_width"
        case fontSize = "font_size"
        case axisColor = "axis_color"
        case xTickDirection = "x_tick_direction"
        case xTickLength = "x_tick_length"
        case yTickLength = "y_tick_length"
        case titleFontSize = "title_font_size"
        case xLabelFontSize = "x_label_font_size"
        case yLabelFontSize = "y_label_font_size"
        case xTickLabelFontSize = "x_tick_label_font_size"
        case yTickLabelFontSize = "y_tick_label_font_size"
        case xLabelRotation = "x_label_rotation"
        case hideAxes = "hide_axes"
        case majorGrid = "major_grid"
        case majorGridColor = "major_grid_color"
        case majorGridThickness = "major_grid_thickness"
        case minorGrid = "minor_grid"
        case minorGridColor = "minor_grid_color"
        case minorGridThickness = "minor_grid_thickness"
        case plotAreaColor = "plot_area_color"
        case pageBackground = "page_background"
        case globalFontName = "global_font_name"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = (try? c.decode(String.self, forKey: .title)) ?? ""
        xLabel = (try? c.decode(String.self, forKey: .xLabel)) ?? ""
        yLabel = (try? c.decode(String.self, forKey: .yLabel)) ?? ""
        xScale = (try? c.decode(String.self, forKey: .xScale)) ?? "linear"
        yScale = (try? c.decode(String.self, forKey: .yScale)) ?? "linear"
        xRange = try? c.decode([Double].self, forKey: .xRange)
        yRange = try? c.decode([Double].self, forKey: .yRange)
        yTicks = (try? c.decode([Double].self, forKey: .yTicks)) ?? []
        yTickLabels = (try? c.decode([String].self, forKey: .yTickLabels)) ?? []
        tickDirection = (try? c.decode(String.self, forKey: .tickDirection)) ?? "out"
        spineWidth = (try? c.decode(Double.self, forKey: .spineWidth)) ?? 1.0
        fontSize = (try? c.decode(Double.self, forKey: .fontSize)) ?? 12.0
        axisColor = (try? c.decode(String.self, forKey: .axisColor)) ?? "#222222"
        xTickDirection = (try? c.decode(String.self, forKey: .xTickDirection)) ?? "out"
        xTickLength = (try? c.decode(Double.self, forKey: .xTickLength)) ?? 5.0
        yTickLength = (try? c.decode(Double.self, forKey: .yTickLength)) ?? 5.0
        titleFontSize = (try? c.decode(Double.self, forKey: .titleFontSize)) ?? 14.0
        xLabelFontSize = (try? c.decode(Double.self, forKey: .xLabelFontSize)) ?? 12.0
        yLabelFontSize = (try? c.decode(Double.self, forKey: .yLabelFontSize)) ?? 12.0
        xTickLabelFontSize = (try? c.decode(Double.self, forKey: .xTickLabelFontSize)) ?? 10.0
        yTickLabelFontSize = (try? c.decode(Double.self, forKey: .yTickLabelFontSize)) ?? 10.0
        xLabelRotation = (try? c.decode(Double.self, forKey: .xLabelRotation)) ?? 0.0
        hideAxes = (try? c.decode(String.self, forKey: .hideAxes)) ?? "show_both"
        majorGrid = (try? c.decode(String.self, forKey: .majorGrid)) ?? "none"
        majorGridColor = (try? c.decode(String.self, forKey: .majorGridColor)) ?? "#CCCCCC"
        majorGridThickness = (try? c.decode(Double.self, forKey: .majorGridThickness)) ?? 1.0
        minorGrid = (try? c.decode(String.self, forKey: .minorGrid)) ?? "none"
        minorGridColor = (try? c.decode(String.self, forKey: .minorGridColor)) ?? "#EEEEEE"
        minorGridThickness = (try? c.decode(Double.self, forKey: .minorGridThickness)) ?? 0.5
        plotAreaColor = (try? c.decode(String.self, forKey: .plotAreaColor)) ?? "clear"
        pageBackground = (try? c.decode(String.self, forKey: .pageBackground)) ?? "clear"
        globalFontName = (try? c.decode(String.self, forKey: .globalFontName)) ?? "Helvetica"
    }
}

// MARK: - JSONValue (recursive type for arbitrary JSON payloads)

/// A type-safe representation of arbitrary JSON values.
/// Used for the `data` field on ChartSpec to carry chart-type-specific payloads.
public indirect enum JSONValue: Decodable, Equatable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case array([JSONValue])
    case object([String: JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let b = try? container.decode(Bool.self) {
            self = .bool(b)
        } else if let d = try? container.decode(Double.self) {
            self = .number(d)
        } else if let s = try? container.decode(String.self) {
            self = .string(s)
        } else if let arr = try? container.decode([JSONValue].self) {
            self = .array(arr)
        } else if let obj = try? container.decode([String: JSONValue].self) {
            self = .object(obj)
        } else {
            self = .null
        }
    }

    /// Extract as String, or nil.
    public var stringValue: String? {
        if case .string(let s) = self { return s }
        return nil
    }

    /// Extract as Double, or nil.
    public var doubleValue: Double? {
        if case .number(let d) = self { return d }
        return nil
    }

    /// Extract as array of JSONValue, or nil.
    public var arrayValue: [JSONValue]? {
        if case .array(let a) = self { return a }
        return nil
    }

    /// Extract as dictionary, or nil.
    public var objectValue: [String: JSONValue]? {
        if case .object(let o) = self { return o }
        return nil
    }

    /// Extract as array of Strings.
    public var stringArray: [String]? {
        arrayValue?.compactMap(\.stringValue)
    }

    /// Extract as array of Doubles.
    public var doubleArray: [Double]? {
        arrayValue?.compactMap(\.doubleValue)
    }
}


// MARK: - AnyCodable helper

public struct AnyCodable: Decodable {
    public let value: Any

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let s = try? container.decode(String.self) {
            value = s
        } else if let d = try? container.decode(Double.self) {
            value = d
        } else if let i = try? container.decode(Int.self) {
            value = i
        } else if let b = try? container.decode(Bool.self) {
            value = b
        } else {
            value = ""
        }
    }

    public var stringValue: String {
        if let s = value as? String { return s }
        if let d = value as? Double { return String(d) }
        if let i = value as? Int { return String(i) }
        return String(describing: value)
    }
}

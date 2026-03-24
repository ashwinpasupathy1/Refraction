// ChartSpec.swift — Decodable structs matching the Python analysis engine's
// renderer-independent ChartSpec JSON schema.
//
// The Python /render endpoint returns:
//   { "ok": true, "spec": <Plotly JSON> }
//
// For native rendering we decode the Plotly JSON into a renderer-independent
// ChartSpec that the SwiftUI Canvas renderers consume directly.

import Foundation

// MARK: - Top-level response wrapper

/// The JSON envelope returned by POST /render.
struct RenderResponse: Decodable {
    let ok: Bool
    let spec: ChartSpec?
    let error: String?
}

// MARK: - ChartSpec (renderer-independent)

/// Top-level chart specification decoded from the Python analysis engine.
/// Maps Plotly's `{ data: [...], layout: {...} }` structure into a form
/// suitable for native Core Graphics rendering.
struct ChartSpec: Decodable {
    let chartType: String
    let groups: [GroupData]
    let style: StyleSpec
    let axes: AxisSpec
    let stats: StatsResult?
    let brackets: [Bracket]
    let referenceLine: ReferenceLine?

    enum CodingKeys: String, CodingKey {
        case chartType = "chart_type"
        case groups, style, axes, stats, brackets
        case referenceLine = "reference_line"
    }

    /// Decode from Plotly JSON format (`{ data: [...], layout: {...} }`).
    /// Transforms Plotly traces + layout into our renderer-independent model.
    init(from decoder: Decoder) throws {
        // Try our native format first
        if let container = try? decoder.container(keyedBy: CodingKeys.self),
           let ct = try? container.decode(String.self, forKey: .chartType) {
            chartType = ct
            groups = (try? container.decode([GroupData].self, forKey: .groups)) ?? []
            style = (try? container.decode(StyleSpec.self, forKey: .style)) ?? StyleSpec()
            axes = (try? container.decode(AxisSpec.self, forKey: .axes)) ?? AxisSpec()
            stats = try? container.decode(StatsResult.self, forKey: .stats)
            brackets = (try? container.decode([Bracket].self, forKey: .brackets)) ?? []
            referenceLine = try? container.decode(ReferenceLine.self, forKey: .referenceLine)
            return
        }

        // Fall back to Plotly JSON format
        let container = try decoder.container(keyedBy: PlotlyCodingKeys.self)
        let traces = (try? container.decode([PlotlyTrace].self, forKey: .data)) ?? []
        let layout = (try? container.decode(PlotlyLayout.self, forKey: .layout)) ?? PlotlyLayout()

        chartType = "bar" // inferred from trace type or overridden by caller
        groups = traces.enumerated().map { idx, trace in
            GroupData(
                name: trace.name ?? "Group \(idx + 1)",
                values: ValuesData(
                    raw: trace.y ?? [],
                    mean: trace.y?.first,
                    sem: trace.errorY?.array?.first,
                    sd: nil,
                    ci95: nil,
                    n: trace.y?.count ?? 0
                ),
                color: trace.markerColor ?? StyleSpec.defaultColors[idx % StyleSpec.defaultColors.count]
            )
        }
        style = StyleSpec(
            colors: traces.compactMap { $0.markerColor },
            showPoints: false,
            showBrackets: true,
            pointSize: 6.0,
            pointAlpha: 0.8,
            barWidth: 0.6,
            errorType: "sem",
            axisStyle: "open"
        )
        axes = AxisSpec(
            title: layout.title?.text ?? "",
            xLabel: layout.xaxis?.title?.text ?? "",
            yLabel: layout.yaxis?.title?.text ?? "",
            xScale: "linear",
            yScale: "linear",
            xRange: nil,
            yRange: nil,
            tickDirection: "out",
            spineWidth: 1.0,
            fontSize: Double(layout.font?.size ?? 12)
        )
        stats = nil
        brackets = []
        referenceLine = nil
    }

    /// Memberwise initializer for programmatic construction.
    init(
        chartType: String = "bar",
        groups: [GroupData] = [],
        style: StyleSpec = StyleSpec(),
        axes: AxisSpec = AxisSpec(),
        stats: StatsResult? = nil,
        brackets: [Bracket] = [],
        referenceLine: ReferenceLine? = nil
    ) {
        self.chartType = chartType
        self.groups = groups
        self.style = style
        self.axes = axes
        self.stats = stats
        self.brackets = brackets
        self.referenceLine = referenceLine
    }
}

// MARK: - Group and Values

/// One data group (e.g. one bar, one box, one series).
struct GroupData: Decodable, Identifiable {
    var id: String { name }
    let name: String
    let values: ValuesData
    let color: String

    enum CodingKeys: String, CodingKey {
        case name, values, color
    }
}

/// Numeric values for a single group — raw data plus precomputed summary stats.
struct ValuesData: Decodable {
    let raw: [Double]
    let mean: Double?
    let sem: Double?
    let sd: Double?
    let ci95: Double?
    let n: Int

    init(raw: [Double] = [], mean: Double? = nil, sem: Double? = nil,
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
struct StatsResult: Decodable {
    let testName: String
    let pValue: Double?
    let statistic: Double?
    let comparisons: [Comparison]
    let normality: NormalityResult?
    let effectSize: Double?
    let warning: String?

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
struct Comparison: Decodable {
    let group1: String
    let group2: String
    let pValue: Double
    let significant: Bool
    let label: String  // e.g. "***", "ns"

    enum CodingKeys: String, CodingKey {
        case group1 = "group_1"
        case group2 = "group_2"
        case pValue = "p_value"
        case significant, label
    }
}

/// Normality test results for the dataset.
struct NormalityResult: Decodable {
    let testName: String
    let pValue: Double
    let isNormal: Bool
    let warning: String?

    enum CodingKeys: String, CodingKey {
        case testName = "test_name"
        case pValue = "p_value"
        case isNormal = "is_normal"
        case warning
    }
}

/// A significance bracket drawn between two groups.
struct Bracket: Decodable {
    let leftIndex: Int
    let rightIndex: Int
    let label: String        // e.g. "***", "ns", "p=0.023"
    let stackingOrder: Int   // vertical position (0 = lowest bracket)

    enum CodingKeys: String, CodingKey {
        case leftIndex = "left_index"
        case rightIndex = "right_index"
        case label
        case stackingOrder = "stacking_order"
    }
}

/// Horizontal reference line.
struct ReferenceLine: Decodable {
    let y: Double
    let label: String
}

// MARK: - Style

/// Visual style parameters for the chart.
struct StyleSpec: Decodable {
    let colors: [String]
    let showPoints: Bool
    let showBrackets: Bool
    let pointSize: Double
    let pointAlpha: Double
    let barWidth: Double
    let errorType: String  // "sem", "sd", "ci95"
    let axisStyle: String  // "open", "closed", "floating", "none"

    static let defaultColors = [
        "#E8453C", "#2274A5", "#32936F", "#F18F01", "#A846A0",
        "#6B4226", "#048A81", "#D4AC0D", "#3B1F2B", "#44BBA4",
    ]

    init(
        colors: [String] = defaultColors,
        showPoints: Bool = false,
        showBrackets: Bool = true,
        pointSize: Double = 6.0,
        pointAlpha: Double = 0.8,
        barWidth: Double = 0.6,
        errorType: String = "sem",
        axisStyle: String = "open"
    ) {
        self.colors = colors
        self.showPoints = showPoints
        self.showBrackets = showBrackets
        self.pointSize = pointSize
        self.pointAlpha = pointAlpha
        self.barWidth = barWidth
        self.errorType = errorType
        self.axisStyle = axisStyle
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
    }
}

// MARK: - Axes

/// Axis configuration.
struct AxisSpec: Decodable {
    let title: String
    let xLabel: String
    let yLabel: String
    let xScale: String  // "linear", "log"
    let yScale: String
    let xRange: [Double]?
    let yRange: [Double]?
    let tickDirection: String  // "out", "in", "inout", ""
    let spineWidth: Double
    let fontSize: Double

    init(
        title: String = "",
        xLabel: String = "",
        yLabel: String = "",
        xScale: String = "linear",
        yScale: String = "linear",
        xRange: [Double]? = nil,
        yRange: [Double]? = nil,
        tickDirection: String = "out",
        spineWidth: Double = 1.0,
        fontSize: Double = 12.0
    ) {
        self.title = title
        self.xLabel = xLabel
        self.yLabel = yLabel
        self.xScale = xScale
        self.yScale = yScale
        self.xRange = xRange
        self.yRange = yRange
        self.tickDirection = tickDirection
        self.spineWidth = spineWidth
        self.fontSize = fontSize
    }

    enum CodingKeys: String, CodingKey {
        case title
        case xLabel = "x_label"
        case yLabel = "y_label"
        case xScale = "x_scale"
        case yScale = "y_scale"
        case xRange = "x_range"
        case yRange = "y_range"
        case tickDirection = "tick_direction"
        case spineWidth = "spine_width"
        case fontSize = "font_size"
    }
}

// MARK: - Plotly JSON intermediate types (for decoding /render responses)

private enum PlotlyCodingKeys: String, CodingKey {
    case data, layout
}

private struct PlotlyTrace: Decodable {
    let x: [AnyCodable]?
    let y: [Double]?
    let name: String?
    let markerColor: String?
    let errorY: PlotlyErrorY?

    enum CodingKeys: String, CodingKey {
        case x, y, name
        case markerColor = "marker_color"
        case errorY = "error_y"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        x = try? container.decode([AnyCodable].self, forKey: .x)
        y = try? container.decode([Double].self, forKey: .y)
        name = try? container.decode(String.self, forKey: .name)
        errorY = try? container.decode(PlotlyErrorY.self, forKey: .errorY)

        // Plotly uses nested marker.color
        if let mc = try? container.decode(String.self, forKey: .markerColor) {
            markerColor = mc
        } else {
            // Try decoding from a nested "marker" object
            struct Marker: Decodable { let color: String? }
            enum MarkerKey: String, CodingKey { case marker }
            if let markerContainer = try? decoder.container(keyedBy: MarkerKey.self),
               let marker = try? markerContainer.decode(Marker.self, forKey: .marker) {
                markerColor = marker.color
            } else {
                markerColor = nil
            }
        }
    }
}

private struct PlotlyErrorY: Decodable {
    let type: String?
    let array: [Double]?
    let visible: Bool?
}

private struct PlotlyLayout: Decodable {
    let title: PlotlyTitle?
    let xaxis: PlotlyAxis?
    let yaxis: PlotlyAxis?
    let font: PlotlyFont?

    init(title: PlotlyTitle? = nil, xaxis: PlotlyAxis? = nil,
         yaxis: PlotlyAxis? = nil, font: PlotlyFont? = nil) {
        self.title = title
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.font = font
    }
}

private struct PlotlyTitle: Decodable {
    let text: String?
}

private struct PlotlyAxis: Decodable {
    let title: PlotlyTitle?
}

private struct PlotlyFont: Decodable {
    let size: Int?
}

// MARK: - AnyCodable helper (for mixed-type arrays like Plotly x-values)

struct AnyCodable: Decodable {
    let value: Any

    init(from decoder: Decoder) throws {
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

    var stringValue: String {
        if let s = value as? String { return s }
        if let d = value as? Double { return String(d) }
        if let i = value as? Int { return String(i) }
        return String(describing: value)
    }
}

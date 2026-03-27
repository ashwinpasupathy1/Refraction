// ChartConfig.swift — Observable configuration model with ~40 properties
// organized by tab (Data, Labels, Style, Stats). Produces the config dict
// sent to the Python /render endpoint.

import Foundation
import SwiftUI

@Observable
final class ChartConfig {

    // MARK: - Data tab

    var sheet: Int = 0

    // MARK: - Labels tab

    var title: String = ""
    var xlabel: String = ""
    var ylabel: String = ""

    // MARK: - Style tab — error bars & points

    var errorType: ErrorType = .sem
    var showPoints: Bool = false
    var jitter: Double = 0.15
    var pointSize: Double = 6.0
    var pointAlpha: Double = 0.80

    // MARK: - Style tab — axes

    var axisStyle: AxisStyle = .open
    var tickDirection: TickDirection = .out
    var minorTicks: Bool = false
    var spineWidth: Double = 0.8

    // MARK: - Style tab — layout

    var figWidth: Double = 5.0
    var figHeight: Double = 5.0
    var fontSize: Double = 12.0
    var barWidth: Double = 0.6
    var lineWidth: Double = 1.5
    var markerStyle: String = "o"
    var markerSize: Double = 6.0

    // MARK: - Style tab — colors & background

    var figBackground: String = "white"
    var gridStyle: GridStyle = .none
    var alpha: Double = 0.85
    var capSize: Double = 4.0

    // MARK: - Style tab — scale

    var yScale: String = "linear"
    var yMin: String = ""
    var yMax: String = ""
    var yTickInterval: Double = 0.0
    var xTickInterval: Double = 0.0

    // MARK: - Style tab — reference line

    var refLineValue: String = ""
    var refLineLabel: String = ""

    // MARK: - Stats tab

    var statsTest: String = "auto"
    var posthoc: String = "tukey"
    var mcCorrection: String = "holm"
    var control: String = ""
    var showNs: Bool = true
    var showPValues: Bool = false
    var showEffectSize: Bool = false
    var showTestName: Bool = false
    var showNormalityWarning: Bool = true
    var pThreshold: Double = 0.05
    var bracketStyle: String = "bracket"

    // MARK: - Enums

    enum ErrorType: String, CaseIterable, Identifiable {
        case sem = "SEM"
        case sd = "SD"
        case ci95 = "CI 95%"

        var id: String { rawValue }

        var apiKey: String {
            switch self {
            case .sem:  return "sem"
            case .sd:   return "sd"
            case .ci95: return "ci95"
            }
        }
    }

    enum AxisStyle: String, CaseIterable, Identifiable {
        case open = "Open (Prism default)"
        case closed = "Closed box"
        case floating = "Floating"
        case none = "None"

        var id: String { rawValue }

        var apiKey: String {
            switch self {
            case .open:     return "open"
            case .closed:   return "closed"
            case .floating: return "floating"
            case .none:     return "none"
            }
        }
    }

    enum TickDirection: String, CaseIterable, Identifiable {
        case out = "Outward (default)"
        case `in` = "Inward"
        case `inout` = "Both"
        case none = "None"

        var id: String { rawValue }

        var apiKey: String {
            switch self {
            case .out:   return "out"
            case .in:    return "in"
            case .inout: return "inout"
            case .none:  return ""
            }
        }
    }

    enum GridStyle: String, CaseIterable, Identifiable {
        case none = "None"
        case horizontal = "Horizontal"
        case full = "Full"

        var id: String { rawValue }

        var apiKey: String {
            switch self {
            case .none:       return "none"
            case .horizontal: return "horizontal"
            case .full:       return "full"
            }
        }
    }

    // MARK: - Serialize to API dict

    /// Produces the flat kwargs dict expected by the Python /render endpoint.
    func toDict() -> [String: Any] {
        var d: [String: Any] = [
            "excel_path": "",
            "sheet": sheet,

            // Labels
            "title": title,
            "xlabel": xlabel,
            "ytitle": ylabel,

            // Style
            "error": errorType.apiKey,
            "show_points": showPoints,
            "jitter": jitter,
            "point_size": pointSize,
            "point_alpha": pointAlpha,
            "axis_style": axisStyle.apiKey,
            "tick_dir": tickDirection.apiKey,
            "minor_ticks": minorTicks,
            "spine_width": spineWidth,

            // Layout
            "figsize": [figWidth, figHeight],
            "font_size": fontSize,
            "bar_width": barWidth,
            "line_width": lineWidth,
            "marker_style": markerStyle,
            "marker_size": markerSize,

            // Colors & background
            "fig_bg": figBackground,
            "grid_style": gridStyle.apiKey,
            "alpha": alpha,
            "cap_size": capSize,

            // Scale
            "yscale": yScale,
            "ytick_interval": yTickInterval,
            "xtick_interval": xTickInterval,

            // Stats
            "stats_test": statsTest,
            "posthoc": posthoc,
            "mc_correction": mcCorrection,
            "control": control,
            "show_ns": showNs,
            "show_p_values": showPValues,
            "show_effect_size": showEffectSize,
            "show_test_name": showTestName,
            "show_normality_warning": showNormalityWarning,
            "p_sig_threshold": pThreshold,
            "bracket_style": bracketStyle,
        ]

        // Optional y-axis limits
        if let min = Double(yMin), let max = Double(yMax) {
            d["ylim"] = [min, max]
        }

        // Optional reference line
        if let refVal = Double(refLineValue) {
            d["ref_line"] = refVal
            d["ref_line_label"] = refLineLabel
        }

        return d
    }

    /// Populate from a dict (inverse of toDict, used when loading .refract files).
    func loadFromDict(_ d: [String: Any]) {
        // excel_path no longer used — data is inline
        sheet = d["sheet"] as? Int ?? sheet
        title = d["title"] as? String ?? title
        xlabel = d["xlabel"] as? String ?? xlabel
        ylabel = d["ytitle"] as? String ?? d["ylabel"] as? String ?? ylabel
        if let e = d["error"] as? String {
            errorType = ErrorType.allCases.first { $0.apiKey == e } ?? errorType
        }
        showPoints = d["show_points"] as? Bool ?? showPoints
        jitter = d["jitter"] as? Double ?? jitter
        pointSize = d["point_size"] as? Double ?? pointSize
        pointAlpha = d["point_alpha"] as? Double ?? pointAlpha
        if let a = d["axis_style"] as? String {
            axisStyle = AxisStyle.allCases.first { $0.apiKey == a } ?? axisStyle
        }
        if let t = d["tick_dir"] as? String {
            tickDirection = TickDirection.allCases.first { $0.apiKey == t } ?? tickDirection
        }
        minorTicks = d["minor_ticks"] as? Bool ?? minorTicks
        spineWidth = d["spine_width"] as? Double ?? spineWidth
        if let fs = d["figsize"] as? [Double], fs.count == 2 {
            figWidth = fs[0]; figHeight = fs[1]
        }
        fontSize = d["font_size"] as? Double ?? fontSize
        barWidth = d["bar_width"] as? Double ?? barWidth
        lineWidth = d["line_width"] as? Double ?? lineWidth
        markerStyle = d["marker_style"] as? String ?? markerStyle
        markerSize = d["marker_size"] as? Double ?? markerSize
        figBackground = d["fig_bg"] as? String ?? figBackground
        if let g = d["grid_style"] as? String {
            gridStyle = GridStyle.allCases.first { $0.apiKey == g } ?? gridStyle
        }
        alpha = d["alpha"] as? Double ?? alpha
        capSize = d["cap_size"] as? Double ?? capSize
        yScale = d["yscale"] as? String ?? yScale
        yTickInterval = d["ytick_interval"] as? Double ?? yTickInterval
        xTickInterval = d["xtick_interval"] as? Double ?? xTickInterval
        if let ylim = d["ylim"] as? [Double], ylim.count == 2 {
            yMin = String(ylim[0]); yMax = String(ylim[1])
        }
        if let rv = d["ref_line"] as? Double {
            refLineValue = String(rv)
            refLineLabel = d["ref_line_label"] as? String ?? ""
        }
        statsTest = d["stats_test"] as? String ?? statsTest
        posthoc = d["posthoc"] as? String ?? posthoc
        mcCorrection = d["mc_correction"] as? String ?? mcCorrection
        control = d["control"] as? String ?? control
        showNs = d["show_ns"] as? Bool ?? showNs
        showPValues = d["show_p_values"] as? Bool ?? showPValues
        showEffectSize = d["show_effect_size"] as? Bool ?? showEffectSize
        showTestName = d["show_test_name"] as? Bool ?? showTestName
        showNormalityWarning = d["show_normality_warning"] as? Bool ?? showNormalityWarning
        pThreshold = d["p_sig_threshold"] as? Double ?? pThreshold
        bracketStyle = d["bracket_style"] as? String ?? bracketStyle
    }

    /// Reset all config values to defaults.
    func resetToDefaults() {
        // excelPath removed — data is inline
        sheet = 0
        title = ""
        xlabel = ""
        ylabel = ""
        errorType = .sem
        showPoints = false
        jitter = 0.15
        pointSize = 6.0
        pointAlpha = 0.80
        axisStyle = .open
        tickDirection = .out
        minorTicks = false
        spineWidth = 0.8
        figWidth = 5.0
        figHeight = 5.0
        fontSize = 12.0
        barWidth = 0.6
        lineWidth = 1.5
        markerStyle = "o"
        markerSize = 6.0
        figBackground = "white"
        gridStyle = .none
        alpha = 0.85
        capSize = 4.0
        yScale = "linear"
        yMin = ""
        yMax = ""
        yTickInterval = 0.0
        xTickInterval = 0.0
        refLineValue = ""
        refLineLabel = ""
        statsTest = "auto"
        posthoc = "tukey"
        mcCorrection = "holm"
        control = ""
        showNs = true
        showPValues = false
        showEffectSize = false
        showTestName = false
        showNormalityWarning = true
        pThreshold = 0.05
        bracketStyle = "bracket"
    }
}

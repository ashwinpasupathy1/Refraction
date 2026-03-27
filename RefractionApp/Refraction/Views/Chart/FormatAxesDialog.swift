// FormatAxesDialog.swift — Prism-style "Format Axes" dialog.
// Controls renderer-only axis formatting — nothing here calls the engine.

import SwiftUI

struct FormatAxesDialog: View {

    @Bindable var settings: FormatAxesSettings
    @Environment(\.dismiss) private var dismiss

    @State private var selectedTab: Tab = .frameAndOrigin

    // Snapshot for cancel — restored if user clicks Cancel
    @State private var snapshot: Data?

    enum Tab: String, CaseIterable {
        case frameAndOrigin = "Frame & Origin"
        case xAxis = "X Axis"
        case leftYAxis = "Left Y Axis"
        case titlesFonts = "Titles & Fonts"
    }

    var body: some View {
        VStack(spacing: 0) {
            // Tab bar
            HStack(spacing: 0) {
                ForEach(Tab.allCases, id: \.rawValue) { tab in
                    Button {
                        selectedTab = tab
                    } label: {
                        Text(tab.rawValue)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.plain)
                    .background(selectedTab == tab ? Color.accentColor.opacity(0.15) : Color.clear)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
            }
            .padding(8)

            Divider()

            // Content
            ScrollView {
                switch selectedTab {
                case .frameAndOrigin:
                    frameAndOriginTab
                case .xAxis:
                    xAxisTab
                case .leftYAxis:
                    leftYAxisTab
                case .titlesFonts:
                    titlesFontsTab
                }
            }
            .frame(minHeight: 400)

            Divider()

            // Bottom buttons
            HStack {
                Spacer()
                Button("Cancel") {
                    DebugLog.shared.logUI("FormatAxesDialog cancelled")
                    restoreSnapshot()
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
                Button("Done") {
                    DebugLog.shared.logUI("FormatAxesDialog applied")
                    dismiss()
                }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
            }
            .padding(12)
        }
        .frame(width: 560)
        .onAppear { takeSnapshot() }
    }

    // MARK: - Snapshot / Restore

    private func takeSnapshot() {
        snapshot = try? JSONEncoder().encode(settings)
    }

    private func restoreSnapshot() {
        guard let data = snapshot,
              let restored = try? JSONDecoder().decode(FormatAxesSettings.self, from: data) else { return }
        settings.originMode = restored.originMode
        settings.yIntersectsXAt = restored.yIntersectsXAt
        settings.xIntersectsYAt = restored.xIntersectsYAt
        settings.chartWidth = restored.chartWidth
        settings.chartHeight = restored.chartHeight
        settings.axisThickness = restored.axisThickness
        settings.axisColor = restored.axisColor
        settings.plotAreaColor = restored.plotAreaColor
        settings.pageBackground = restored.pageBackground
        settings.frameStyle = restored.frameStyle
        settings.hideAxes = restored.hideAxes
        settings.majorGrid = restored.majorGrid
        settings.majorGridColor = restored.majorGridColor
        settings.majorGridThickness = restored.majorGridThickness
        settings.minorGrid = restored.minorGrid
        settings.minorGridColor = restored.minorGridColor
        settings.minorGridThickness = restored.minorGridThickness
        settings.xAxisTitle = restored.xAxisTitle
        settings.xAxisTitleFontSize = restored.xAxisTitleFontSize
        settings.xAxisTickDirection = restored.xAxisTickDirection
        settings.xAxisTickLength = restored.xAxisTickLength
        settings.xAxisLabelFontSize = restored.xAxisLabelFontSize
        settings.xAxisLabelRotation = restored.xAxisLabelRotation
        settings.yAxisTitle = restored.yAxisTitle
        settings.yAxisTitleFontSize = restored.yAxisTitleFontSize
        settings.yAxisTickDirection = restored.yAxisTickDirection
        settings.yAxisTickLength = restored.yAxisTickLength
        settings.yAxisLabelFontSize = restored.yAxisLabelFontSize
        settings.yAxisAutoRange = restored.yAxisAutoRange
        settings.yAxisMin = restored.yAxisMin
        settings.yAxisMax = restored.yAxisMax
        settings.yAxisTickInterval = restored.yAxisTickInterval
        settings.yAxisScale = restored.yAxisScale
        settings.chartTitle = restored.chartTitle
        settings.chartTitleFontSize = restored.chartTitleFontSize
        settings.globalFontName = restored.globalFontName
    }

    // MARK: - Frame & Origin Tab

    private var frameAndOriginTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            // Origin
            GroupBox("Origin") {
                VStack(alignment: .leading, spacing: 8) {
                    Picker("Origin mode:", selection: $settings.originMode) {
                        ForEach(FormatAxesSettings.OriginMode.allCases) {
                            Text($0.label).tag($0)
                        }
                    }
                    .frame(width: 280)

                    if settings.originMode == .manual {
                        HStack {
                            Text("Y intersects X at:")
                            TextField("", value: $settings.yIntersectsXAt, format: .number)
                                .frame(width: 80)
                            Spacer()
                            Text("X intersects Y at:")
                            TextField("", value: $settings.xIntersectsYAt, format: .number)
                                .frame(width: 80)
                        }
                    }
                }
            }

            // Shape & Size
            GroupBox("Shape & Size") {
                HStack {
                    Text("Width:")
                    TextField("", value: $settings.chartWidth, format: .number)
                        .frame(width: 60)
                    Text("in")
                    Spacer()
                    Text("Height:")
                    TextField("", value: $settings.chartHeight, format: .number)
                        .frame(width: 60)
                    Text("in")
                }
            }

            // Axes & Colors
            GroupBox("Axes & Colors") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Axis thickness:")
                        Slider(value: $settings.axisThickness, in: 0.5...4, step: 0.5)
                            .frame(width: 100)
                        Text("\(settings.axisThickness, specifier: "%.1f") pt")
                            .monospacedDigit()
                            .frame(width: 45)
                        Spacer()
                        Text("Axis color:")
                        ColorPicker("", selection: hexBinding($settings.axisColor))
                            .labelsHidden()
                    }
                    HStack {
                        Picker("Hide axes:", selection: $settings.hideAxes) {
                            ForEach(FormatAxesSettings.HideAxes.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 240)
                        Spacer()
                        Picker("Frame:", selection: $settings.frameStyle) {
                            ForEach(FormatAxesSettings.FrameStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 180)
                    }
                    HStack {
                        Text("Plot area:")
                        ColorPicker("", selection: hexBinding($settings.plotAreaColor))
                            .labelsHidden()
                        Spacer()
                        Text("Page background:")
                        ColorPicker("", selection: hexBinding($settings.pageBackground))
                            .labelsHidden()
                    }
                }
            }

            // Grid Lines
            GroupBox("Grid Lines") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Major grid:")
                        Picker("", selection: $settings.majorGrid) {
                            ForEach(FormatAxesSettings.GridLineStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        if settings.majorGrid != .none {
                            ColorPicker("", selection: hexBinding($settings.majorGridColor))
                                .labelsHidden()
                            Text("Thickness:")
                            Slider(value: $settings.majorGridThickness, in: 0.5...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(settings.majorGridThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                    HStack {
                        Text("Minor grid:")
                        Picker("", selection: $settings.minorGrid) {
                            ForEach(FormatAxesSettings.GridLineStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        if settings.minorGrid != .none {
                            ColorPicker("", selection: hexBinding($settings.minorGridColor))
                                .labelsHidden()
                            Text("Thickness:")
                            Slider(value: $settings.minorGridThickness, in: 0.25...2, step: 0.25)
                                .frame(width: 80)
                            Text("\(settings.minorGridThickness, specifier: "%.2f") pt")
                                .monospacedDigit()
                                .frame(width: 50)
                        }
                    }
                }
            }
        }
        .padding()
    }

    // MARK: - X Axis Tab

    private var xAxisTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            GroupBox("Title") {
                HStack {
                    Text("X axis title:")
                    TextField("", text: $settings.xAxisTitle)
                    Spacer()
                    Text("Size:")
                    TextField("", value: $settings.xAxisTitleFontSize, format: .number)
                        .frame(width: 50)
                    Text("pt")
                }
            }

            GroupBox("Ticks") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Direction:")
                        Picker("", selection: $settings.xAxisTickDirection) {
                            ForEach(FormatAxesSettings.TickDir.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        Spacer()
                        Text("Length:")
                        Slider(value: $settings.xAxisTickLength, in: 0...15, step: 1)
                            .frame(width: 100)
                        Text("\(Int(settings.xAxisTickLength)) pt")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                }
            }

            GroupBox("Labels") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Font size:")
                        TextField("", value: $settings.xAxisLabelFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                        Spacer()
                        Text("Rotation:")
                        Slider(value: $settings.xAxisLabelRotation, in: 0...90, step: 15)
                            .frame(width: 100)
                        Text("\(Int(settings.xAxisLabelRotation))\u{00B0}")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                }
            }
        }
        .padding()
    }

    // MARK: - Left Y Axis Tab

    private var leftYAxisTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            GroupBox("Title") {
                HStack {
                    Text("Y axis title:")
                    TextField("", text: $settings.yAxisTitle)
                    Spacer()
                    Text("Size:")
                    TextField("", value: $settings.yAxisTitleFontSize, format: .number)
                        .frame(width: 50)
                    Text("pt")
                }
            }

            GroupBox("Ticks") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Direction:")
                        Picker("", selection: $settings.yAxisTickDirection) {
                            ForEach(FormatAxesSettings.TickDir.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        Spacer()
                        Text("Length:")
                        Slider(value: $settings.yAxisTickLength, in: 0...15, step: 1)
                            .frame(width: 100)
                        Text("\(Int(settings.yAxisTickLength)) pt")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                    HStack {
                        Text("Label font size:")
                        TextField("", value: $settings.yAxisLabelFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                    }
                }
            }

            GroupBox("Range") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Auto range", isOn: $settings.yAxisAutoRange)
                        .fontWeight(.semibold)

                    if !settings.yAxisAutoRange {
                        HStack {
                            Text("Min:")
                            TextField("", value: $settings.yAxisMin, format: .number)
                                .frame(width: 80)
                            Spacer()
                            Text("Max:")
                            TextField("", value: $settings.yAxisMax, format: .number)
                                .frame(width: 80)
                        }
                    }

                    HStack {
                        Text("Tick interval:")
                        TextField("", value: $settings.yAxisTickInterval, format: .number)
                            .frame(width: 80)
                        Text("(0 = auto)")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                }
            }

            GroupBox("Scale") {
                Picker("Scale type:", selection: $settings.yAxisScale) {
                    ForEach(FormatAxesSettings.ScaleType.allCases) {
                        Text($0.label).tag($0)
                    }
                }
                .frame(width: 200)
            }
        }
        .padding()
    }

    // MARK: - Titles & Fonts Tab

    private var titlesFontsTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            GroupBox("Chart Title") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Title:")
                        TextField("", text: $settings.chartTitle)
                    }
                    HStack {
                        Text("Font size:")
                        TextField("", value: $settings.chartTitleFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                    }
                }
            }

            GroupBox("Global Font") {
                HStack {
                    Text("Font name:")
                    TextField("", text: $settings.globalFontName)
                        .frame(width: 200)
                }
            }
        }
        .padding()
    }

    // MARK: - Hex color binding helper

    private func hexBinding(_ binding: Binding<String>) -> Binding<Color> {
        Binding(
            get: {
                if binding.wrappedValue == "clear" {
                    return Color.clear
                }
                return Color(hex: binding.wrappedValue)
            },
            set: { newColor in
                if let components = NSColor(newColor).usingColorSpace(.sRGB) {
                    let r = Int(components.redComponent * 255)
                    let g = Int(components.greenComponent * 255)
                    let b = Int(components.blueComponent * 255)
                    binding.wrappedValue = String(format: "#%02X%02X%02X", r, g, b)
                }
            }
        )
    }
}

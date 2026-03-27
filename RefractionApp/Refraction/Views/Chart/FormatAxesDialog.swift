// FormatAxesDialog.swift — Prism-style "Format Axes" dialog.
// Edits a local copy of settings. Done commits changes and re-renders.

import SwiftUI

struct FormatAxesDialog: View {

    /// The real settings on the Graph — only written to on Done.
    var settings: FormatAxesSettings
    @Environment(\.dismiss) private var dismiss
    @Environment(AppState.self) private var appState

    @State private var selectedTab: Tab = .frameAndOrigin
    @State private var isApplying = false

    /// Local working copy — all controls bind to this, not the real settings.
    @State private var draft = FormatAxesSettings()

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
                Button("Cancel") {
                    DebugLog.shared.logUI("FormatAxesDialog cancelled")
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
                Spacer()
                Button("Done") {
                    commitAndRender()
                }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
                    .disabled(isApplying)
            }
            .padding(12)
        }
        .frame(width: 560)
        .onAppear { loadDraft() }
    }

    // MARK: - Draft management

    /// Copy real settings into the local draft for editing.
    private func loadDraft() {
        guard let data = try? JSONEncoder().encode(settings),
              let copy = try? JSONDecoder().decode(FormatAxesSettings.self, from: data) else { return }
        draft = copy
    }

    /// Write draft back to the real settings and trigger a re-render.
    private func commitAndRender() {
        DebugLog.shared.logUI("FormatAxesDialog done — committing changes")
        isApplying = true

        // Copy every property from draft → real settings
        settings.originMode = draft.originMode
        settings.yIntersectsXAt = draft.yIntersectsXAt
        settings.xIntersectsYAt = draft.xIntersectsYAt
        settings.chartWidth = draft.chartWidth
        settings.chartHeight = draft.chartHeight
        settings.axisThickness = draft.axisThickness
        settings.axisColor = draft.axisColor
        settings.plotAreaColor = draft.plotAreaColor
        settings.pageBackground = draft.pageBackground
        settings.frameStyle = draft.frameStyle
        settings.hideAxes = draft.hideAxes
        settings.majorGrid = draft.majorGrid
        settings.majorGridColor = draft.majorGridColor
        settings.majorGridThickness = draft.majorGridThickness
        settings.minorGrid = draft.minorGrid
        settings.minorGridColor = draft.minorGridColor
        settings.minorGridThickness = draft.minorGridThickness
        settings.xAxisTitle = draft.xAxisTitle
        settings.xAxisTitleFontSize = draft.xAxisTitleFontSize
        settings.xAxisTickDirection = draft.xAxisTickDirection
        settings.xAxisTickLength = draft.xAxisTickLength
        settings.xAxisLabelFontSize = draft.xAxisLabelFontSize
        settings.xAxisLabelRotation = draft.xAxisLabelRotation
        settings.yAxisTitle = draft.yAxisTitle
        settings.yAxisTitleFontSize = draft.yAxisTitleFontSize
        settings.yAxisTickDirection = draft.yAxisTickDirection
        settings.yAxisTickLength = draft.yAxisTickLength
        settings.yAxisLabelFontSize = draft.yAxisLabelFontSize
        settings.yAxisAutoRange = draft.yAxisAutoRange
        settings.yAxisMin = draft.yAxisMin
        settings.yAxisMax = draft.yAxisMax
        settings.yAxisTickInterval = draft.yAxisTickInterval
        settings.yAxisScale = draft.yAxisScale
        settings.chartTitle = draft.chartTitle
        settings.chartTitleFontSize = draft.chartTitleFontSize
        settings.globalFontName = draft.globalFontName

        appState.hasUnsavedChanges = true

        Task {
            await appState.generatePlot()
            DebugLog.shared.logAppEvent("FormatAxesDialog done — re-render complete")
            isApplying = false
            dismiss()
        }
    }

    // MARK: - Frame & Origin Tab

    private var frameAndOriginTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            // Origin
            GroupBox("Origin") {
                VStack(alignment: .leading, spacing: 8) {
                    Picker("Origin mode:", selection: $draft.originMode) {
                        ForEach(FormatAxesSettings.OriginMode.allCases) {
                            Text($0.label).tag($0)
                        }
                    }
                    .frame(width: 280)

                    if draft.originMode == .manual {
                        HStack {
                            Text("Y intersects X at:")
                            TextField("", value: $draft.yIntersectsXAt, format: .number)
                                .frame(width: 80)
                            Spacer()
                            Text("X intersects Y at:")
                            TextField("", value: $draft.xIntersectsYAt, format: .number)
                                .frame(width: 80)
                        }
                    }
                }
            }

            // Shape & Size
            GroupBox("Shape & Size") {
                HStack {
                    Text("Width:")
                    TextField("", value: $draft.chartWidth, format: .number)
                        .frame(width: 60)
                    Text("in")
                    Spacer()
                    Text("Height:")
                    TextField("", value: $draft.chartHeight, format: .number)
                        .frame(width: 60)
                    Text("in")
                }
            }

            // Axes & Colors
            GroupBox("Axes & Colors") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Axis thickness:")
                        Slider(value: $draft.axisThickness, in: 0.5...4, step: 0.5)
                            .frame(width: 100)
                        Text("\(draft.axisThickness, specifier: "%.1f") pt")
                            .monospacedDigit()
                            .frame(width: 45)
                        Spacer()
                        Text("Axis color:")
                        ColorPicker("", selection: hexBinding($draft.axisColor))
                            .labelsHidden()
                    }
                    HStack {
                        Picker("Hide axes:", selection: $draft.hideAxes) {
                            ForEach(FormatAxesSettings.HideAxes.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 240)
                        Spacer()
                        Picker("Frame:", selection: $draft.frameStyle) {
                            ForEach(FormatAxesSettings.FrameStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 180)
                    }
                    HStack {
                        Text("Plot area:")
                        ColorPicker("", selection: hexBinding($draft.plotAreaColor))
                            .labelsHidden()
                        Spacer()
                        Text("Page background:")
                        ColorPicker("", selection: hexBinding($draft.pageBackground))
                            .labelsHidden()
                    }
                }
            }

            // Grid Lines
            GroupBox("Grid Lines") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Major grid:")
                        Picker("", selection: $draft.majorGrid) {
                            ForEach(FormatAxesSettings.GridLineStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        if draft.majorGrid != .none {
                            ColorPicker("", selection: hexBinding($draft.majorGridColor))
                                .labelsHidden()
                            Text("Thickness:")
                            Slider(value: $draft.majorGridThickness, in: 0.5...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(draft.majorGridThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                    HStack {
                        Text("Minor grid:")
                        Picker("", selection: $draft.minorGrid) {
                            ForEach(FormatAxesSettings.GridLineStyle.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        if draft.minorGrid != .none {
                            ColorPicker("", selection: hexBinding($draft.minorGridColor))
                                .labelsHidden()
                            Text("Thickness:")
                            Slider(value: $draft.minorGridThickness, in: 0.25...2, step: 0.25)
                                .frame(width: 80)
                            Text("\(draft.minorGridThickness, specifier: "%.2f") pt")
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
                    TextField("", text: $draft.xAxisTitle)
                    Spacer()
                    Text("Size:")
                    TextField("", value: $draft.xAxisTitleFontSize, format: .number)
                        .frame(width: 50)
                    Text("pt")
                }
            }

            GroupBox("Ticks") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Direction:")
                        Picker("", selection: $draft.xAxisTickDirection) {
                            ForEach(FormatAxesSettings.TickDir.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        Spacer()
                        Text("Length:")
                        Slider(value: $draft.xAxisTickLength, in: 0...15, step: 1)
                            .frame(width: 100)
                        Text("\(Int(draft.xAxisTickLength)) pt")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                }
            }

            GroupBox("Labels") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Font size:")
                        TextField("", value: $draft.xAxisLabelFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                        Spacer()
                        Text("Rotation:")
                        Slider(value: $draft.xAxisLabelRotation, in: 0...90, step: 15)
                            .frame(width: 100)
                        Text("\(Int(draft.xAxisLabelRotation))\u{00B0}")
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
                    TextField("", text: $draft.yAxisTitle)
                    Spacer()
                    Text("Size:")
                    TextField("", value: $draft.yAxisTitleFontSize, format: .number)
                        .frame(width: 50)
                    Text("pt")
                }
            }

            GroupBox("Ticks") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Direction:")
                        Picker("", selection: $draft.yAxisTickDirection) {
                            ForEach(FormatAxesSettings.TickDir.allCases) {
                                Text($0.label).tag($0)
                            }
                        }
                        .frame(width: 90)
                        Spacer()
                        Text("Length:")
                        Slider(value: $draft.yAxisTickLength, in: 0...15, step: 1)
                            .frame(width: 100)
                        Text("\(Int(draft.yAxisTickLength)) pt")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                    HStack {
                        Text("Label font size:")
                        TextField("", value: $draft.yAxisLabelFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                    }
                }
            }

            GroupBox("Range") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Auto range", isOn: $draft.yAxisAutoRange)
                        .fontWeight(.semibold)

                    if !draft.yAxisAutoRange {
                        HStack {
                            Text("Min:")
                            TextField("", value: $draft.yAxisMin, format: .number)
                                .frame(width: 80)
                            Spacer()
                            Text("Max:")
                            TextField("", value: $draft.yAxisMax, format: .number)
                                .frame(width: 80)
                        }
                    }

                    HStack {
                        Text("Tick interval:")
                        TextField("", value: $draft.yAxisTickInterval, format: .number)
                            .frame(width: 80)
                        Text("(0 = auto)")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                }
            }

            GroupBox("Scale") {
                Picker("Scale type:", selection: $draft.yAxisScale) {
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
                        TextField("", text: $draft.chartTitle)
                    }
                    HStack {
                        Text("Font size:")
                        TextField("", value: $draft.chartTitleFontSize, format: .number)
                            .frame(width: 50)
                        Text("pt")
                    }
                }
            }

            GroupBox("Global Font") {
                HStack {
                    Text("Font name:")
                    TextField("", text: $draft.globalFontName)
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

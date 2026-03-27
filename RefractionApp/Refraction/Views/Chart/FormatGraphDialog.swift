// FormatGraphDialog.swift — Prism-style "Format Graph" dialog.
// Edits a local copy of settings. Done commits changes and re-renders.

import SwiftUI
import RefractionRenderer

struct FormatGraphDialog: View {

    /// The real settings on the Graph — only written to on Done.
    var settings: FormatGraphSettings
    @Environment(\.dismiss) private var dismiss
    @Environment(AppState.self) private var appState

    @State private var selectedTab: Tab = .appearance
    @State private var isApplying = false

    /// Local working copy — all controls bind to this, not the real settings.
    @State private var draft = FormatGraphSettings()

    enum Tab: String, CaseIterable {
        case appearance = "Appearance"
        case graphSettings = "Graph Settings"
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
                case .appearance:
                    appearanceTab
                case .graphSettings:
                    graphSettingsTab
                }
            }
            .frame(minHeight: 400)

            Divider()

            // Bottom buttons
            HStack {
                Button("Cancel") {
                    DebugLog.shared.logUI("FormatGraphDialog cancelled")
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
        .frame(width: 520)
        .onAppear { loadDraft() }
    }

    // MARK: - Draft management

    /// Copy real settings into the local draft for editing.
    private func loadDraft() {
        guard let data = try? JSONEncoder().encode(settings),
              let copy = try? JSONDecoder().decode(FormatGraphSettings.self, from: data) else { return }
        draft = copy
    }

    /// Write draft back to the real settings and trigger a re-render.
    private func commitAndRender() {
        DebugLog.shared.logUI("FormatGraphDialog done — committing changes")
        isApplying = true

        // Copy every property from draft → real settings
        settings.showSymbols = draft.showSymbols
        settings.symbolColor = draft.symbolColor
        settings.symbolShape = draft.symbolShape
        settings.symbolSize = draft.symbolSize
        settings.symbolBorderColor = draft.symbolBorderColor
        settings.symbolBorderThickness = draft.symbolBorderThickness
        settings.showBars = draft.showBars
        settings.barColor = draft.barColor
        settings.barWidth = draft.barWidth
        settings.barFillOpacity = draft.barFillOpacity
        settings.barBorderColor = draft.barBorderColor
        settings.barBorderThickness = draft.barBorderThickness
        settings.barPattern = draft.barPattern
        settings.barsBeginAtY = draft.barsBeginAtY
        settings.showErrorBars = draft.showErrorBars
        settings.errorBarColor = draft.errorBarColor
        settings.errorBarDirection = draft.errorBarDirection
        settings.errorBarStyle = draft.errorBarStyle
        settings.errorBarThickness = draft.errorBarThickness
        settings.showConnectingLine = draft.showConnectingLine
        settings.lineColor = draft.lineColor
        settings.lineThickness = draft.lineThickness
        settings.lineStyle = draft.lineStyle
        settings.connectMeans = draft.connectMeans
        settings.startAtOrigin = draft.startAtOrigin
        settings.showAreaFill = draft.showAreaFill
        settings.areaFillColor = draft.areaFillColor
        settings.areaFillPosition = draft.areaFillPosition
        settings.areaFillAlpha = draft.areaFillAlpha
        settings.showLegend = draft.showLegend
        settings.labelPoints = draft.labelPoints

        appState.hasUnsavedChanges = true

        Task {
            await appState.generatePlot()
            DebugLog.shared.logAppEvent("FormatGraphDialog done — re-render complete")
            isApplying = false
            dismiss()
        }
    }

    // MARK: - Appearance Tab

    private var appearanceTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            // Show symbols
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show symbols", isOn: $draft.showSymbols)
                        .fontWeight(.semibold)

                    if draft.showSymbols {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($draft.symbolColor))
                                .labelsHidden()
                            Spacer()
                            Text("Shape:")
                            Picker("", selection: $draft.symbolShape) {
                                ForEach(FormatGraphSettings.SymbolShape.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 100)
                        }
                        HStack {
                            Text("Size:")
                            Slider(value: $draft.symbolSize, in: 2...20, step: 1)
                            Text("\(Int(draft.symbolSize)) pt")
                                .monospacedDigit()
                                .frame(width: 40)
                            Spacer()
                            Text("Border:")
                            Slider(value: $draft.symbolBorderThickness, in: 0...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(draft.symbolBorderThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show bars
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show bars/spikes/droplines", isOn: $draft.showBars)
                        .fontWeight(.semibold)

                    if draft.showBars {
                        HStack {
                            Text("Width:")
                            Slider(value: $draft.barWidth, in: 0.1...1.0, step: 0.05)
                            Text("\(draft.barWidth, specifier: "%.2f")")
                                .monospacedDigit()
                                .frame(width: 40)
                            Spacer()
                            Text("Pattern:")
                            Picker("", selection: $draft.barPattern) {
                                ForEach(FormatGraphSettings.BarPattern.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Border color:")
                            ColorPicker("", selection: hexBinding($draft.barBorderColor))
                                .labelsHidden()
                            Text("Border thickness:")
                            Slider(value: $draft.barBorderThickness, in: 0...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(draft.barBorderThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show error bars
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show error bars", isOn: $draft.showErrorBars)
                        .fontWeight(.semibold)

                    if draft.showErrorBars {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($draft.errorBarColor))
                                .labelsHidden()
                            Spacer()
                            Text("Dir.:")
                            Picker("", selection: $draft.errorBarDirection) {
                                ForEach(FormatGraphSettings.ErrorBarDirection.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                            Spacer()
                            Text("Style:")
                            Picker("", selection: $draft.errorBarStyle) {
                                ForEach(FormatGraphSettings.ErrorBarStyle.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Thickness:")
                            Slider(value: $draft.errorBarThickness, in: 0.5...4, step: 0.5)
                            Text("\(draft.errorBarThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show connecting line
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show connecting line/curve", isOn: $draft.showConnectingLine)
                        .fontWeight(.semibold)

                    if draft.showConnectingLine {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($draft.lineColor))
                                .labelsHidden()
                            Spacer()
                            Text("Thickness:")
                            Slider(value: $draft.lineThickness, in: 0.5...6, step: 0.5)
                                .frame(width: 100)
                            Text("\(draft.lineThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                        HStack {
                            Text("Style:")
                            Picker("", selection: $draft.lineStyle) {
                                ForEach(FormatGraphSettings.LineStyle.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                            Spacer()
                            Toggle("Start at origin", isOn: $draft.startAtOrigin)
                        }
                    }
                }
            }

            // Show area fill
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show area fill", isOn: $draft.showAreaFill)
                        .fontWeight(.semibold)

                    if draft.showAreaFill {
                        HStack {
                            Text("Fill color:")
                            ColorPicker("", selection: hexBinding($draft.areaFillColor))
                                .labelsHidden()
                            Spacer()
                            Text("Position:")
                            Picker("", selection: $draft.areaFillPosition) {
                                ForEach(FormatGraphSettings.AreaFillPosition.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Opacity:")
                            Slider(value: $draft.areaFillAlpha, in: 0.05...1.0, step: 0.05)
                            Text("\(Int(draft.areaFillAlpha * 100))%")
                                .monospacedDigit()
                                .frame(width: 40)
                        }
                    }
                }
            }
        }
        .padding()
    }

    // MARK: - Graph Settings Tab

    private var graphSettingsTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            GroupBox("Legend") {
                Toggle("Show legend", isOn: $draft.showLegend)
            }

            GroupBox("Labels") {
                Toggle("Label each point with its row title", isOn: $draft.labelPoints)
            }
        }
        .padding()
    }

    // MARK: - Hex color binding helper

    private func hexBinding(_ binding: Binding<String>) -> Binding<Color> {
        Binding(
            get: { Color(hex: binding.wrappedValue) },
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

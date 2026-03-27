// FormatGraphDialog.swift — Prism-style "Format Graph" dialog.
// Controls renderer-only visual settings — nothing here calls the engine.

import SwiftUI
import RefractionRenderer

struct FormatGraphDialog: View {

    @Bindable var settings: FormatGraphSettings
    @Environment(\.dismiss) private var dismiss

    @State private var selectedTab: Tab = .appearance

    // Snapshot for cancel — restored if user clicks Cancel
    @State private var snapshot: Data?

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
                Spacer()
                Button("Cancel") {
                    DebugLog.shared.logUI("FormatGraphDialog cancelled")
                    restoreSnapshot()
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)
                Button("Done") {
                    DebugLog.shared.logUI("FormatGraphDialog applied")
                    dismiss()
                }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
            }
            .padding(12)
        }
        .frame(width: 520)
        .onAppear { takeSnapshot() }
    }

    // MARK: - Snapshot / Restore

    private func takeSnapshot() {
        snapshot = try? JSONEncoder().encode(settings)
    }

    private func restoreSnapshot() {
        guard let data = snapshot,
              let restored = try? JSONDecoder().decode(FormatGraphSettings.self, from: data) else { return }
        settings.showSymbols = restored.showSymbols
        settings.symbolColor = restored.symbolColor
        settings.symbolShape = restored.symbolShape
        settings.symbolSize = restored.symbolSize
        settings.symbolBorderColor = restored.symbolBorderColor
        settings.symbolBorderThickness = restored.symbolBorderThickness
        settings.showBars = restored.showBars
        settings.barColor = restored.barColor
        settings.barWidth = restored.barWidth
        settings.barFillOpacity = restored.barFillOpacity
        settings.barBorderColor = restored.barBorderColor
        settings.barBorderThickness = restored.barBorderThickness
        settings.barPattern = restored.barPattern
        settings.barsBeginAtY = restored.barsBeginAtY
        settings.showErrorBars = restored.showErrorBars
        settings.errorBarColor = restored.errorBarColor
        settings.errorBarDirection = restored.errorBarDirection
        settings.errorBarStyle = restored.errorBarStyle
        settings.errorBarThickness = restored.errorBarThickness
        settings.showConnectingLine = restored.showConnectingLine
        settings.lineColor = restored.lineColor
        settings.lineThickness = restored.lineThickness
        settings.lineStyle = restored.lineStyle
        settings.connectMeans = restored.connectMeans
        settings.startAtOrigin = restored.startAtOrigin
        settings.showAreaFill = restored.showAreaFill
        settings.areaFillColor = restored.areaFillColor
        settings.areaFillPosition = restored.areaFillPosition
        settings.areaFillAlpha = restored.areaFillAlpha
        settings.showLegend = restored.showLegend
        settings.labelPoints = restored.labelPoints
    }

    // MARK: - Appearance Tab

    private var appearanceTab: some View {
        VStack(alignment: .leading, spacing: 16) {

            // Show symbols
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show symbols", isOn: $settings.showSymbols)
                        .fontWeight(.semibold)

                    if settings.showSymbols {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($settings.symbolColor))
                                .labelsHidden()
                            Spacer()
                            Text("Shape:")
                            Picker("", selection: $settings.symbolShape) {
                                ForEach(FormatGraphSettings.SymbolShape.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 100)
                        }
                        HStack {
                            Text("Size:")
                            Slider(value: $settings.symbolSize, in: 2...20, step: 1)
                            Text("\(Int(settings.symbolSize)) pt")
                                .monospacedDigit()
                                .frame(width: 40)
                            Spacer()
                            Text("Border:")
                            Slider(value: $settings.symbolBorderThickness, in: 0...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(settings.symbolBorderThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show bars
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show bars/spikes/droplines", isOn: $settings.showBars)
                        .fontWeight(.semibold)

                    if settings.showBars {
                        HStack {
                            Text("Width:")
                            Slider(value: $settings.barWidth, in: 0.1...1.0, step: 0.05)
                            Text("\(settings.barWidth, specifier: "%.2f")")
                                .monospacedDigit()
                                .frame(width: 40)
                            Spacer()
                            Text("Pattern:")
                            Picker("", selection: $settings.barPattern) {
                                ForEach(FormatGraphSettings.BarPattern.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Border color:")
                            ColorPicker("", selection: hexBinding($settings.barBorderColor))
                                .labelsHidden()
                            Text("Border thickness:")
                            Slider(value: $settings.barBorderThickness, in: 0...4, step: 0.5)
                                .frame(width: 80)
                            Text("\(settings.barBorderThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show error bars
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show error bars", isOn: $settings.showErrorBars)
                        .fontWeight(.semibold)

                    if settings.showErrorBars {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($settings.errorBarColor))
                                .labelsHidden()
                            Spacer()
                            Text("Dir.:")
                            Picker("", selection: $settings.errorBarDirection) {
                                ForEach(FormatGraphSettings.ErrorBarDirection.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                            Spacer()
                            Text("Style:")
                            Picker("", selection: $settings.errorBarStyle) {
                                ForEach(FormatGraphSettings.ErrorBarStyle.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Thickness:")
                            Slider(value: $settings.errorBarThickness, in: 0.5...4, step: 0.5)
                            Text("\(settings.errorBarThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                    }
                }
            }

            // Show connecting line
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show connecting line/curve", isOn: $settings.showConnectingLine)
                        .fontWeight(.semibold)

                    if settings.showConnectingLine {
                        HStack {
                            Text("Color:")
                            ColorPicker("", selection: hexBinding($settings.lineColor))
                                .labelsHidden()
                            Spacer()
                            Text("Thickness:")
                            Slider(value: $settings.lineThickness, in: 0.5...6, step: 0.5)
                                .frame(width: 100)
                            Text("\(settings.lineThickness, specifier: "%.1f") pt")
                                .monospacedDigit()
                                .frame(width: 45)
                        }
                        HStack {
                            Text("Style:")
                            Picker("", selection: $settings.lineStyle) {
                                ForEach(FormatGraphSettings.LineStyle.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                            Spacer()
                            Toggle("Start at origin", isOn: $settings.startAtOrigin)
                        }
                    }
                }
            }

            // Show area fill
            GroupBox {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show area fill", isOn: $settings.showAreaFill)
                        .fontWeight(.semibold)

                    if settings.showAreaFill {
                        HStack {
                            Text("Fill color:")
                            ColorPicker("", selection: hexBinding($settings.areaFillColor))
                                .labelsHidden()
                            Spacer()
                            Text("Position:")
                            Picker("", selection: $settings.areaFillPosition) {
                                ForEach(FormatGraphSettings.AreaFillPosition.allCases) {
                                    Text($0.label).tag($0)
                                }
                            }
                            .frame(width: 80)
                        }
                        HStack {
                            Text("Opacity:")
                            Slider(value: $settings.areaFillAlpha, in: 0.05...1.0, step: 0.05)
                            Text("\(Int(settings.areaFillAlpha * 100))%")
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
                Toggle("Show legend", isOn: $settings.showLegend)
            }

            GroupBox("Labels") {
                Toggle("Label each point with its row title", isOn: $settings.labelPoints)
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

// DataTabView.swift — Configuration panel for data, labels, and basic style.
// Includes file picker, label fields, error type, and Generate button.

import SwiftUI
import UniformTypeIdentifiers

struct DataTabView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        @Bindable var config = appState.chartConfig

        ScrollView {
            VStack(alignment: .leading, spacing: 20) {

                // MARK: - Data section
                sectionHeader("Data")

                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text(fileDisplayName)
                            .lineLimit(1)
                            .truncationMode(.middle)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .foregroundStyle(config.excelPath.isEmpty ? .secondary : .primary)

                        Button("Choose File...") {
                            openFilePicker()
                        }
                        .controlSize(.small)
                    }

                    LabeledContent("Sheet") {
                        TextField("Sheet", value: $config.sheet, format: .number)
                            .textFieldStyle(.roundedBorder)
                            .frame(width: 60)
                    }
                }

                Divider()

                // MARK: - Labels section
                sectionHeader("Labels")

                VStack(alignment: .leading, spacing: 8) {
                    LabeledContent("Title") {
                        TextField("Chart title", text: $config.title)
                            .textFieldStyle(.roundedBorder)
                    }

                    LabeledContent("X Label") {
                        TextField("X axis label", text: $config.xlabel)
                            .textFieldStyle(.roundedBorder)
                    }

                    LabeledContent("Y Label") {
                        TextField("Y axis label", text: $config.ylabel)
                            .textFieldStyle(.roundedBorder)
                    }
                }

                Divider()

                // MARK: - Style section
                sectionHeader("Style")

                VStack(alignment: .leading, spacing: 8) {
                    if appState.selectedChartType.hasErrorBars {
                        LabeledContent("Error Bars") {
                            Picker("", selection: $config.errorType) {
                                ForEach(ChartConfig.ErrorType.allCases) { type in
                                    Text(type.rawValue).tag(type)
                                }
                            }
                            .labelsHidden()
                            .frame(width: 100)
                        }
                    }

                    if appState.selectedChartType.hasPoints {
                        Toggle("Show data points", isOn: $config.showPoints)

                        if config.showPoints {
                            LabeledContent("Point size") {
                                Slider(value: $config.pointSize, in: 2...16, step: 1)
                                    .frame(width: 120)
                            }

                            LabeledContent("Opacity") {
                                Slider(value: $config.pointAlpha, in: 0.1...1.0, step: 0.05)
                                    .frame(width: 120)
                            }
                        }
                    }

                    LabeledContent("Axis Style") {
                        Picker("", selection: $config.axisStyle) {
                            ForEach(ChartConfig.AxisStyle.allCases) { style in
                                Text(style.rawValue).tag(style)
                            }
                        }
                        .labelsHidden()
                        .frame(width: 160)
                    }
                }

                Divider()

                // MARK: - Generate
                Button {
                    Task { await appState.generatePlot() }
                } label: {
                    HStack {
                        Image(systemName: "play.fill")
                        Text("Generate Plot")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(appState.isLoading || config.excelPath.isEmpty)

                Spacer()
            }
            .padding()
        }
        .navigationTitle("Configuration")
    }

    // MARK: - Helpers

    private var fileDisplayName: String {
        if appState.chartConfig.excelPath.isEmpty {
            return "No file selected"
        }
        return URL(fileURLWithPath: appState.chartConfig.excelPath).lastPathComponent
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(.primary)
    }

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType(filenameExtension: "xlsx")!,
            UTType(filenameExtension: "xls")!,
            UTType(filenameExtension: "csv")!,
        ]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.message = "Select an Excel or CSV data file"

        guard panel.runModal() == .OK, let url = panel.url else { return }

        // Upload to the server so the Python engine can access it
        Task {
            await appState.uploadFile(url: url)
        }
    }
}

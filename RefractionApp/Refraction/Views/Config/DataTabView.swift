// DataTabView.swift — Configuration panel for data, labels, and basic style.
// Includes data table picker, file picker, label fields, and error type.

import SwiftUI

struct DataTabView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        if let graph = appState.activeGraph,
           let experiment = appState.activeExperiment {
            @Bindable var config = graph.chartConfig
            let chartType = graph.chartType
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {

                    // MARK: - Data Table picker
                    sectionHeader("Data")

                    VStack(alignment: .leading, spacing: 8) {
                        LabeledContent("Data Table") {
                            Picker("", selection: Bindable(graph).dataTableID) {
                                ForEach(experiment.dataTables) { table in
                                    Text(table.label).tag(table.id)
                                }
                            }
                            .labelsHidden()
                            .frame(maxWidth: .infinity)
                            .onChange(of: graph.dataTableID) { _, _ in
                                // Data table switch handled — data is now in-memory
                            }
                        }

                        HStack {
                            let table = appState.activeExperiment?.dataTable(for: graph)
                            Text(table?.originalFileName ?? table?.label ?? "No data")
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .foregroundStyle(table?.hasData == true ? .primary : .secondary)
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
                        if chartType.hasErrorBars {
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

                        if chartType.hasPoints {
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

                    // MARK: - Generate (temporary — will be removed with two-tier reactivity)
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
                    .disabled(appState.isLoading || !(appState.activeExperiment?.dataTable(for: graph)?.hasData ?? false))

                    Spacer()
                }
                .padding()
            }
        } else {
            Text("Select a graph")
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Helpers

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(.primary)
    }

}

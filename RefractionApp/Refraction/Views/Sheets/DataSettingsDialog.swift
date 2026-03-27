// DataSettingsDialog.swift — Dialog for data table, labels, and basic style config.
// Opened from the toolbar Data button. Wraps the same controls as the old DataTabView.

import SwiftUI

struct DataSettingsDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    @State private var isApplying = false

    var body: some View {
        VStack(spacing: 0) {
            // Title
            Text("Data Settings")
                .font(.headline)
                .padding(12)

            Divider()

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

                        // MARK: - Labels
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

                        // MARK: - Error type
                        if chartType.hasErrorBars {
                            sectionHeader("Error Bars")

                            LabeledContent("Error Type") {
                                Picker("", selection: $config.errorType) {
                                    ForEach(ChartConfig.ErrorType.allCases) { type in
                                        Text(type.rawValue).tag(type)
                                    }
                                }
                                .labelsHidden()
                                .frame(width: 100)
                            }

                            Divider()
                        }

                    }
                    .padding()
                }
                .frame(minHeight: 300)
            } else {
                Text("Select a graph first")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            Divider()

            // Bottom buttons
            HStack {
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                Spacer()
                Button("Apply") {
                    DebugLog.shared.logUI("DataSettingsDialog apply clicked")
                    isApplying = true
                    Task {
                        _ = try? await APIClient.shared.health()
                        DebugLog.shared.logAppEvent("DataSettingsDialog apply — dummy server call completed")
                        isApplying = false
                    }
                }
                .disabled(isApplying)
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
            }
            .padding(12)
        }
        .frame(width: 480)
    }

    // MARK: - Helpers

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(.primary)
    }
}

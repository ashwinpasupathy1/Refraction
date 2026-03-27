// InfoSheetView.swift — Notes and metadata editor for a data table.
// Shows the selected data table's info and parent experiment details.

import SwiftUI

struct InfoSheetView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        if let table = appState.activeDataTable,
           let experiment = appState.activeExperiment {
            Form {
                Section("Data Table") {
                    TextField("Name", text: Bindable(table).label)
                    LabeledContent("Type", value: table.tableType.label)
                }

                Section("Data") {
                    if table.hasData {
                        LabeledContent("Data", value: "\(table.rowCount) rows x \(table.columnCount) cols")
                        if let name = table.originalFileName {
                            LabeledContent("Source file", value: name)
                        }
                    } else {
                        LabeledContent("Data", value: "No data loaded")
                    }
                }

                Section("Experiment") {
                    LabeledContent("Name", value: experiment.label)
                    LabeledContent("Data Tables", value: "\(experiment.dataTables.count)")
                    LabeledContent("Graphs", value: "\(experiment.graphs.count)")
                    LabeledContent("Analyses", value: "\(experiment.analyses.count)")
                }

                Section("Notes") {
                    TextEditor(text: Bindable(experiment).info)
                        .font(.body)
                        .frame(minHeight: 120)
                }
            }
            .formStyle(.grouped)
        } else {
            Text("Select a data table")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

// NewExperimentDialog.swift — Dialog for creating a new experiment.
// User enters a name and optional description. Includes helper text
// explaining the experiment structure.

import SwiftUI

struct NewExperimentDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    @State private var name: String = ""
    @State private var description: String = ""

    private var defaultName: String {
        "Experiment \(appState.experiments.count + 1)"
    }

    private var isDuplicate: Bool {
        let trimmed = effectiveName
        return appState.experiments.contains { $0.label.trimmingCharacters(in: .whitespaces) == trimmed }
    }

    private var effectiveName: String {
        let trimmed = name.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? defaultName : trimmed
    }

    var body: some View {
        VStack(spacing: 0) {
            Text("New Experiment")
                .font(.headline)
                .padding(.top, 20)
                .padding(.bottom, 12)

            VStack(alignment: .leading, spacing: 14) {
                // Helper text
                VStack(alignment: .leading, spacing: 6) {
                    Label("What is an experiment?", systemImage: "info.circle")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.blue)

                    Text("An experiment is a container that groups related data, graphs, and analyses together. Each experiment can have multiple data tables (e.g., raw measurements), graphs (e.g., bar chart, scatter plot), and statistical analyses (e.g., t-test results). Use separate experiments for independent studies or conditions.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(10)
                .background(Color.blue.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: 6))

                // Name field
                VStack(alignment: .leading, spacing: 4) {
                    Text("Name")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    TextField(defaultName, text: $name)
                        .textFieldStyle(.roundedBorder)
                        .onSubmit { createIfValid() }

                    if isDuplicate {
                        Label("An experiment named \"\(effectiveName)\" already exists.", systemImage: "exclamationmark.triangle.fill")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                }

                // Description field
                VStack(alignment: .leading, spacing: 4) {
                    Text("Description (optional)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    TextField("Brief description of this experiment...", text: $description, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                        .lineLimit(2...4)
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 20)

            Divider()

            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)

                Button("Create") { createIfValid() }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
                    .disabled(isDuplicate)
            }
            .padding(16)
        }
        .frame(width: 420)
        .fixedSize(horizontal: false, vertical: true)
    }

    private func createIfValid() {
        guard !isDuplicate else { return }
        let exp = appState.addExperiment(label: effectiveName)
        exp.description = description.trimmingCharacters(in: .whitespacesAndNewlines)
        dismiss()
    }
}

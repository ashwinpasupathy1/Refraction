// StatsSettingsDialog.swift — Dialog for statistical test configuration.
// Opened from the toolbar Stats button. Wraps the same controls as StatsTabView.

import SwiftUI

struct StatsSettingsDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss
    @State private var isApplying = false

    var body: some View {
        VStack(spacing: 0) {
            // Title
            Text("Statistics Settings")
                .font(.headline)
                .padding(12)

            Divider()

            if let graph = appState.activeGraph {
                @Bindable var config = graph.chartConfig
                let chartType = graph.chartType

                if chartType.hasStats {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {

                            // MARK: - Test selection
                            sectionHeader("Statistical Test")

                            LabeledContent("Test") {
                                Picker("", selection: $config.statsTest) {
                                    Section("Automatic") {
                                        Text("Auto").tag("auto")
                                        Text("None").tag("none")
                                    }
                                    Section("Parametric") {
                                        Text("Unpaired t-test").tag("t-test")
                                        Text("Welch's t-test").tag("welch_t-test")
                                        Text("One-way ANOVA").tag("anova")
                                        Text("Welch's ANOVA").tag("welch_anova")
                                        Text("Paired t-test").tag("paired")
                                    }
                                    Section("Non-parametric") {
                                        Text("Mann-Whitney U").tag("mann-whitney")
                                        Text("Kruskal-Wallis").tag("kruskal-wallis")
                                    }
                                }
                                .labelsHidden()
                                .frame(width: 180)
                            }

                            LabeledContent("Posthoc") {
                                Picker("", selection: $config.posthoc) {
                                    Text("Tukey HSD").tag("tukey")
                                    Text("Dunn").tag("dunn")
                                    Text("Games-Howell").tag("games_howell")
                                    Text("Dunnett").tag("dunnett")
                                }
                                .labelsHidden()
                                .frame(width: 140)
                            }

                            LabeledContent("Correction") {
                                Picker("", selection: $config.mcCorrection) {
                                    Text("Holm-Bonferroni").tag("holm")
                                    Text("Bonferroni").tag("bonferroni")
                                    Text("Benjamini-Hochberg").tag("fdr_bh")
                                    Text("None").tag("none")
                                }
                                .labelsHidden()
                                .frame(width: 160)
                            }

                            Divider()

                            // MARK: - Comparison mode
                            sectionHeader("Comparisons")

                            LabeledContent("Control Group") {
                                TextField("none", text: $config.control)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 120)
                            }

                            LabeledContent("p-threshold") {
                                TextField("0.05", value: $config.pThreshold, format: .number)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 70)
                            }

                            LabeledContent("Bracket Style") {
                                Picker("", selection: $config.bracketStyle) {
                                    Text("Bracket").tag("bracket")
                                    Text("Line").tag("line")
                                }
                                .labelsHidden()
                                .frame(width: 100)
                            }

                            Divider()

                            // MARK: - Display toggles
                            sectionHeader("Display")

                            Toggle("Show n= counts", isOn: $config.showNs)
                            Toggle("Show p-values", isOn: $config.showPValues)
                            Toggle("Show effect sizes", isOn: $config.showEffectSize)
                            Toggle("Show test name", isOn: $config.showTestName)
                            Toggle("Show normality warning", isOn: $config.showNormalityWarning)
                        }
                        .padding()
                    }
                    .frame(minHeight: 400)
                } else {
                    ContentUnavailableView(
                        "No Statistics",
                        systemImage: "function",
                        description: Text("This chart type does not support statistical tests.")
                    )
                    .frame(minHeight: 200)
                }
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
                    DebugLog.shared.logUI("StatsSettingsDialog apply clicked")
                    isApplying = true
                    Task {
                        _ = try? await APIClient.shared.health()
                        DebugLog.shared.logAppEvent("StatsSettingsDialog apply — dummy server call completed")
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

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .foregroundStyle(.primary)
    }
}

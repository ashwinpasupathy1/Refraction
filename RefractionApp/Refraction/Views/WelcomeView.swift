// WelcomeView.swift — First-run experience shown when no data file is loaded.
// Displays app branding, supported formats, quick-start tips, and a button
// to load bundled sample data.

import SwiftUI
import UniformTypeIdentifiers

struct WelcomeView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            // App icon and title
            VStack(spacing: 12) {
                Image(systemName: "light.beacon.max")
                    .font(.system(size: 56))
                    .foregroundStyle(.linearGradient(
                        colors: [.blue, .purple, .pink],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ))

                Text("Refraction")
                    .font(.system(size: 32, weight: .semibold, design: .rounded))

                Text("Scientific plotting and analysis")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }

            Spacer()
                .frame(height: 40)

            // Action buttons
            VStack(spacing: 12) {
                Button {
                    openFilePicker()
                } label: {
                    Label("Open Data File", systemImage: "doc.badge.plus")
                        .frame(width: 200)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                Button {
                    loadSampleData()
                } label: {
                    Label("Try Sample Data", systemImage: "flask")
                        .frame(width: 200)
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
            }

            Spacer()
                .frame(height: 36)

            // Supported formats
            VStack(spacing: 8) {
                Text("Supported Formats")
                    .font(.headline)
                    .foregroundStyle(.secondary)

                HStack(spacing: 16) {
                    ForEach(supportedFormats, id: \.ext) { format in
                        formatBadge(format.ext, description: format.description)
                    }
                }
            }

            Spacer()
                .frame(height: 28)

            // Quick start tips
            VStack(alignment: .leading, spacing: 8) {
                Text("Quick Start")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)

                VStack(alignment: .leading, spacing: 6) {
                    tipRow(icon: "1.circle.fill", text: "Open a data file or try the sample data")
                    tipRow(icon: "2.circle.fill", text: "Choose a chart type from the sidebar")
                    tipRow(icon: "3.circle.fill", text: "Adjust settings and click Generate")
                }
                .frame(maxWidth: 340)
                .frame(maxWidth: .infinity)
            }

            Spacer()

            // Version
            Text("Version \(appVersion)")
                .font(.caption)
                .foregroundStyle(.quaternary)
                .padding(.bottom, 12)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    // MARK: - Subviews

    private func formatBadge(_ ext: String, description: String) -> some View {
        VStack(spacing: 4) {
            Text(ext)
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(.fill.tertiary, in: RoundedRectangle(cornerRadius: 6))

            Text(description)
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
    }

    private func tipRow(icon: String, text: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .foregroundStyle(.tint)
                .frame(width: 20)
            Text(text)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Data

    private struct FormatInfo {
        let ext: String
        let description: String
    }

    private var supportedFormats: [FormatInfo] {
        [
            FormatInfo(ext: ".xlsx", description: "Excel"),
            FormatInfo(ext: ".xls", description: "Legacy Excel"),
            FormatInfo(ext: ".csv", description: "Comma-separated"),
            FormatInfo(ext: ".pzfx", description: "GraphPad Prism"),
        ]
    }

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.1.0"
    }

    // MARK: - Actions

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType(filenameExtension: "xlsx")!,
            UTType(filenameExtension: "xls")!,
            UTType(filenameExtension: "csv")!,
            UTType(filenameExtension: "pzfx")!,
        ]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.message = "Select a data file to analyze"

        guard panel.runModal() == .OK, let url = panel.url else { return }

        Task {
            await appState.uploadFile(url: url)
        }
    }

    private func loadSampleData() {
        // Try multiple lookup strategies for bundled sample data.
        // Strategy 1: folder reference (subdirectory preserved in bundle)
        // Strategy 2: flat copy (xcodegen group-based resources)
        // Strategy 3: direct path search in bundle resources
        let sampleURL: URL? =
            Bundle.main.url(forResource: "drug_treatment", withExtension: "xlsx", subdirectory: "SampleData")
            ?? Bundle.main.url(forResource: "drug_treatment", withExtension: "xlsx")
            ?? Bundle.main.resourceURL?.appendingPathComponent("SampleData/drug_treatment.xlsx")

        if let url = sampleURL, FileManager.default.fileExists(atPath: url.path) {
            Task {
                await appState.uploadFile(url: url)
            }
        } else {
            // Build diagnostic info so future debugging is easier
            let bundlePath = Bundle.main.bundlePath
            let resourcePath = Bundle.main.resourcePath ?? "(nil)"
            let xlsxFiles = (try? FileManager.default.contentsOfDirectory(
                at: Bundle.main.resourceURL ?? URL(fileURLWithPath: "/"),
                includingPropertiesForKeys: nil
            ).filter { $0.pathExtension == "xlsx" }.map(\.lastPathComponent)) ?? []

            let sampleDirExists = FileManager.default.fileExists(
                atPath: (Bundle.main.resourceURL?.appendingPathComponent("SampleData").path) ?? ""
            )

            appState.error = """
                Sample data file not found in app bundle.
                Bundle: \(bundlePath)
                Resources: \(resourcePath)
                SampleData dir exists: \(sampleDirExists)
                .xlsx files in resources: \(xlsxFiles.isEmpty ? "none" : xlsxFiles.joined(separator: ", "))
                Tip: Run 'xcodegen generate' and rebuild.
                """
        }
    }
}

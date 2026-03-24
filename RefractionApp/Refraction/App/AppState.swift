// AppState.swift — Central observable state for the Refraction app.
// Owns the selected chart type, configuration, current spec, and loading state.

import Foundation

@Observable
final class AppState {

    /// Currently selected chart type in the sidebar.
    var selectedChartType: ChartType = .bar

    /// Configuration panel state (all user-adjustable parameters).
    var chartConfig = ChartConfig()

    /// The most recent ChartSpec returned by the Python engine.
    var currentSpec: ChartSpec?

    /// Whether a render request is in flight.
    var isLoading: Bool = false

    /// Most recent error message (nil = no error).
    var error: String?

    // MARK: - Actions

    /// Send the current configuration to the Python server and store the result.
    @MainActor
    func generatePlot() async {
        guard !chartConfig.excelPath.isEmpty else {
            error = "No data file selected. Choose an Excel or CSV file first."
            return
        }

        isLoading = true
        error = nil

        do {
            let spec = try await APIClient.shared.analyze(
                chartType: selectedChartType,
                config: chartConfig
            )
            currentSpec = spec
        } catch {
            self.error = error.localizedDescription
            currentSpec = nil
        }

        isLoading = false
    }

    /// Upload a local file to the server and set the excel path to the
    /// server-side path returned by /upload.
    @MainActor
    func uploadFile(url: URL) async {
        do {
            let serverPath = try await APIClient.shared.upload(fileURL: url)
            chartConfig.excelPath = serverPath
        } catch {
            self.error = "File upload failed: \(error.localizedDescription)"
        }
    }

    /// Clear the current chart and error state.
    func clearChart() {
        currentSpec = nil
        error = nil
    }
}

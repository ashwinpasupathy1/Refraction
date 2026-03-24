// ContentView.swift — Root view with 3-column NavigationSplitView.
// Sidebar: chart type selector. Content: chart canvas. Detail: config panel.

import SwiftUI

struct ContentView: View {

    @Environment(AppState.self) private var appState
    @Environment(PythonServer.self) private var server

    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            ChartSidebarView()
                .navigationSplitViewColumnWidth(min: 180, ideal: 200, max: 240)
        } content: {
            chartArea
                .navigationSplitViewColumnWidth(min: 400, ideal: 600)
        } detail: {
            DataTabView()
                .navigationSplitViewColumnWidth(min: 260, ideal: 300, max: 360)
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                serverStatusIndicator

                Button {
                    Task { await appState.generatePlot() }
                } label: {
                    Label("Generate", systemImage: "play.fill")
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(appState.isLoading || appState.chartConfig.excelPath.isEmpty)
            }
        }
    }

    // MARK: - Chart area

    @ViewBuilder
    private var chartArea: some View {
        ZStack {
            Color(nsColor: .controlBackgroundColor)
                .ignoresSafeArea()

            if appState.isLoading {
                ProgressView("Generating chart...")
                    .controlSize(.large)
            } else if let error = appState.error {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text(error)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 400)
                }
                .padding()
            } else if appState.currentSpec != nil {
                ChartCanvasView()
            } else {
                VStack(spacing: 16) {
                    Image(systemName: "chart.bar.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(.quaternary)
                    Text("Select a data file and click Generate")
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    // MARK: - Server status

    @ViewBuilder
    private var serverStatusIndicator: some View {
        switch server.state {
        case .idle:
            Label("Server idle", systemImage: "circle")
                .foregroundStyle(.secondary)
                .labelStyle(.iconOnly)
        case .starting:
            ProgressView()
                .controlSize(.small)
                .help("Starting Python server...")
        case .running:
            Image(systemName: "circle.fill")
                .foregroundStyle(.green)
                .help("Python server running on port \(PythonServer.port)")
        case .failed(let msg):
            Image(systemName: "exclamationmark.circle.fill")
                .foregroundStyle(.red)
                .help("Server failed: \(msg)")
        }
    }
}

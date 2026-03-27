// GraphSheetView.swift — Graph view with chart canvas + zoom strip.
// Auto-generates the chart when the graph appears or data changes.
// Format dialogs are opened from the main toolbar ribbon, not from here.

import SwiftUI
import RefractionRenderer

struct GraphSheetView: View {

    @Environment(AppState.self) private var appState
    let graph: Graph

    var body: some View {
        VStack(spacing: 0) {
            // Minimal toolbar (chart type label)
            graphToolbar
            Divider()

            // Main content: chart canvas + zoom strip
            VStack(spacing: 0) {
                chartArea
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                Divider()
                zoomControlStrip
            }
        }
        // Auto-generate only when this graph has no spec and data is available.
        .task(id: "\(graph.id)_\(appState.activeGraphDataTable?.columns.count ?? 0)_\(appState.activeGraphDataTable?.rows.count ?? 0)") {
            guard graph.chartSpec == nil,
                  appState.activeGraphDataTable?.hasData == true else { return }
            DebugLog.shared.logVerbose("auto-generate chart: \(graph.chartType.rawValue)")
            await appState.generatePlot()
        }
    }

    // MARK: - Chart Area

    /// Merge format dialog settings into the engine-provided ChartSpec
    /// so the renderers respect user overrides from Format Graph / Format Axes.
    private var mergedSpec: ChartSpec? {
        guard let baseSpec = graph.chartSpec else { return nil }
        return applyFormatSettings(
            spec: baseSpec,
            graphSettings: graph.formatSettings,
            axesSettings: graph.formatAxesSettings,
            renderStyle: graph.renderStyle
        )
    }

    @ViewBuilder
    private var chartArea: some View {
        if graph.isLoading {
            ProgressView("Generating chart...")
                .controlSize(.large)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let spec = mergedSpec {
            GeometryReader { geo in
                let zoom = graph.zoomLevel
                let scaledWidth = geo.size.width * zoom
                let scaledHeight = geo.size.height * zoom

                ScrollView([.horizontal, .vertical]) {
                    chartCanvas(spec: spec)
                        .frame(width: scaledWidth, height: scaledHeight)
                }
            }
        } else if appState.activeGraphDataTable?.hasData == true {
            ProgressView("Generating chart...")
                .controlSize(.regular)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            Text("Import data into the data table first")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    @ViewBuilder
    private func chartCanvas(spec: ChartSpec) -> some View {
        ChartCanvasView(spec: spec)
    }

    // MARK: - Zoom Control Strip

    private var zoomControlStrip: some View {
        HStack(spacing: 8) {
            Button("Fit") {
                graph.zoomLevel = 1.0
            }
            .controlSize(.small)
            .buttonStyle(.bordered)

            Divider()
                .frame(height: 16)

            Button {
                graph.zoomLevel = max(0.25, graph.zoomLevel - 0.25)
            } label: {
                Image(systemName: "minus")
            }
            .controlSize(.small)
            .buttonStyle(.borderless)
            .disabled(graph.zoomLevel <= 0.25)

            Slider(
                value: Bindable(graph).zoomLevel,
                in: 0.25...4.0,
                step: 0.25
            )
            .frame(width: 120)
            .controlSize(.small)

            Button {
                graph.zoomLevel = min(4.0, graph.zoomLevel + 0.25)
            } label: {
                Image(systemName: "plus")
            }
            .controlSize(.small)
            .buttonStyle(.borderless)
            .disabled(graph.zoomLevel >= 4.0)

            Text("\(Int(graph.zoomLevel * 100))%")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.secondary)
                .frame(width: 40, alignment: .trailing)
        }
        .padding(.horizontal, 12)
        .frame(height: 28)
        .background(.bar)
    }

    // MARK: - Toolbar

    private var graphToolbar: some View {
        HStack {
            Label(graph.chartType.label, systemImage: graph.chartType.sfSymbol)
                .font(.headline)
            if let tableName = appState.activeExperiment?.dataTable(for: graph)?.label {
                Text("→ \(tableName)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.bar)
    }
}

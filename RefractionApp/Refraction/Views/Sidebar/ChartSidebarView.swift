// ChartSidebarView.swift — Chart type selector grouped by category.
// Uses SF Symbols for icons and highlights the selected chart type.

import SwiftUI

struct ChartSidebarView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        @Bindable var state = appState

        List(selection: $state.selectedChartType) {
            ForEach(ChartType.byCategory, id: \.category) { group in
                Section(group.category.rawValue) {
                    ForEach(group.types) { chartType in
                        Label(chartType.label, systemImage: chartType.sfSymbol)
                            .tag(chartType)
                    }
                }
            }
        }
        .listStyle(.sidebar)
        .navigationTitle("Charts")
    }
}

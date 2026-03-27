// NavigatorView.swift — Experiment-based sidebar navigator.
// Each experiment has sections: Data Tables, Graphs, Results.

import SwiftUI

struct NavigatorView: View {

    @Environment(AppState.self) private var appState

    @State private var experimentToDelete: Experiment?
    @State private var editingID: UUID?
    @State private var showAnalyzeDialog = false
    @State private var showNewExperimentDialog = false
    @State private var showNewDataTableDialog = false
    @State private var showNewGraphDialog = false
    @State private var newDataTableExperimentID: UUID?
    @State private var searchText: String = ""
    @State private var expandedExperiments: Set<UUID> = []
    @State private var dropTargetID: UUID?
    @State private var dropEdge: DropEdge = .bottom
    /// True while a drag session is active. Set false in performDrop so
    /// spurious post-drop callbacks from macOS don't re-show the indicator.
    @State private var isDragging: Bool = false
    /// Cached UUID of the item currently being dragged, set on dropEntered
    /// so performDrop can resolve it synchronously (no async loadItem delay).
    @State private var draggedItemID: UUID?
    @State private var lastDropTime: Date?

    enum DropEdge { case top, bottom }

    /// Whether an item matches the current search query.
    private func matches(_ text: String) -> Bool {
        searchText.isEmpty || text.localizedCaseInsensitiveContains(searchText)
    }

    /// Filter an experiment's children, returning only matching items.
    /// Returns nil if nothing in the experiment matches.
    private struct FilteredExperiment {
        let experiment: Experiment
        let dataTables: [DataTable]
        let graphs: [Graph]
        let analyses: [Analysis]
        var hasAnyMatch: Bool { !dataTables.isEmpty || !graphs.isEmpty || !analyses.isEmpty || nameMatches }
        let nameMatches: Bool
    }

    private func filtered(_ experiment: Experiment) -> FilteredExperiment {
        let nameMatches = matches(experiment.label)
        if searchText.isEmpty || nameMatches {
            // Experiment name matches or no search — show everything
            return FilteredExperiment(
                experiment: experiment,
                dataTables: experiment.dataTables,
                graphs: experiment.graphs,
                analyses: experiment.analyses,
                nameMatches: nameMatches
            )
        }
        // Filter children individually
        return FilteredExperiment(
            experiment: experiment,
            dataTables: experiment.dataTables.filter { matches($0.label) || matches($0.tableType.label) },
            graphs: experiment.graphs.filter { matches($0.label) || matches($0.chartType.label) },
            analyses: experiment.analyses.filter { matches($0.label) || matches($0.analysisType ?? "") },
            nameMatches: false
        )
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                newExperimentButton
                Spacer()
                Button {
                    DebugLog.shared.logUI("expand all experiments")
                    expandedExperiments = Set(appState.experiments.map(\.id))
                } label: {
                    Image(systemName: "chevron.down")
                        .font(.caption2.bold())
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("Expand All")

                Button {
                    DebugLog.shared.logUI("collapse all experiments")
                    expandedExperiments.removeAll()
                } label: {
                    Image(systemName: "chevron.up")
                        .font(.caption2.bold())
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("Collapse All")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            // Search bar
            HStack(spacing: 4) {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.tertiary)
                    .font(.caption)
                TextField("Search...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.caption)
                if !searchText.isEmpty {
                    Button {
                        searchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.tertiary)
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color(nsColor: .controlBackgroundColor))

            Divider()

            if appState.experiments.isEmpty {
                emptyState
            } else {
                experimentList
            }
        }
        .listStyle(.sidebar)
        .onChange(of: dropTargetID) { oldVal, newVal in
            DebugLog.shared.logVerbose("dropTargetID: \(oldVal?.uuidString.prefix(8) ?? "nil") → \(newVal?.uuidString.prefix(8) ?? "nil")")
        }
        .onAppear {
            // Only expand the first experiment on launch
            if let first = appState.experiments.first {
                expandedExperiments = [first.id]
            }
        }
        .onChange(of: appState.experiments.count) { oldCount, newCount in
            // Auto-expand only newly added experiments
            if newCount > oldCount, let last = appState.experiments.last {
                expandedExperiments.insert(last.id)
            }
        }
        .alert(
            "Delete Experiment?",
            isPresented: Binding(
                get: { experimentToDelete != nil },
                set: { if !$0 { experimentToDelete = nil } }
            )
        ) {
            Button("Delete", role: .destructive) {
                if let exp = experimentToDelete {
                    appState.removeExperiment(id: exp.id)
                }
                experimentToDelete = nil
            }
            Button("Cancel", role: .cancel) { experimentToDelete = nil }
        } message: {
            if let exp = experimentToDelete {
                Text("Are you sure you want to delete \"\(exp.label)\"? This will remove all data tables, graphs, and analyses.")
            }
        }
        .sheet(isPresented: $showAnalyzeDialog) {
            AnalyzeDataDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showNewExperimentDialog) {
            NewExperimentDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showNewDataTableDialog) {
            NewDataTableDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showNewGraphDialog) {
            NewGraphDialog()
                .environment(appState)
        }
    }

    // MARK: - New Experiment Button

    private var newExperimentButton: some View {
        Button {
            DebugLog.shared.logUI("open NewExperimentDialog")
            showNewExperimentDialog = true
        } label: {
            HStack {
                Image(systemName: "plus.circle.fill")
                Text("New Experiment")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "flask")
                .font(.system(size: 36))
                .foregroundStyle(.quaternary)
            Text("No experiments")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Create a new experiment to get started.")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
            Spacer()
        }
        .padding()
    }

    // MARK: - Experiment List

    /// Pre-built lookup: item UUID → (experimentID, kind). Avoids linear scan on every click.
    private var itemKindMap: [UUID: (experimentID: UUID, kind: ItemKind)] {
        var map: [UUID: (UUID, ItemKind)] = [:]
        for exp in appState.experiments {
            for t in exp.dataTables { map[t.id] = (exp.id, .dataTable) }
            for g in exp.graphs { map[g.id] = (exp.id, .graph) }
            for a in exp.analyses { map[a.id] = (exp.id, .analysis) }
        }
        return map
    }

    @ViewBuilder
    private var experimentList: some View {
        let kindMap = itemKindMap
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                ForEach(appState.experiments) { experiment in
                    let f = filtered(experiment)
                    if f.hasAnyMatch {
                        experimentSection(experiment, filtered: f, kindMap: kindMap)
                    }
                }
            }
        }
        // Disable implicit animations on the drop indicator so it vanishes instantly
        .animation(.none, value: dropTargetID)
    }

    // MARK: - Experiment Section

    private func selectItem(_ id: UUID, kindMap: [UUID: (experimentID: UUID, kind: ItemKind)]) {
        guard let entry = kindMap[id] else { return }
        appState.activeExperimentID = entry.experimentID
        appState.activeItemID = id
        appState.activeItemKind = entry.kind
        DebugLog.shared.logUI("select \(entry.kind.rawValue)", detail: "id: \(id.uuidString.prefix(8))")
    }

    @ViewBuilder
    private func experimentSection(_ experiment: Experiment, filtered f: FilteredExperiment, kindMap: [UUID: (experimentID: UUID, kind: ItemKind)]) -> some View {
        let isExpanded = expandedExperiments.contains(experiment.id)

        // Header row with manual chevron
        Button {
            if expandedExperiments.contains(experiment.id) {
                expandedExperiments.remove(experiment.id)
                DebugLog.shared.logUI("collapse \(experiment.label)")
            } else {
                expandedExperiments.insert(experiment.id)
                DebugLog.shared.logUI("expand \(experiment.label)")
            }
        } label: {
            HStack(spacing: 4) {
                Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(.tertiary)
                    .frame(width: 12)
                experimentHeader(experiment)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 5)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .draggable(experiment.id.uuidString)
        .overlay(alignment: dropEdge == .top ? .top : .bottom) {
            if isDragging && dropTargetID == experiment.id {
                Rectangle()
                    .fill(Color.accentColor)
                    .frame(height: 2)
            }
        }
        .onDrop(of: [.text], delegate: ReorderDropDelegate(
            targetID: experiment.id,
            dropTargetID: $dropTargetID,
            dropEdge: $dropEdge,
            isDragging: $isDragging, draggedItemID: $draggedItemID, lastDropTime: $lastDropTime,
            onDrop: { droppedID, edge in
                guard droppedID != experiment.id,
                      let fromIndex = appState.experiments.firstIndex(where: { $0.id == droppedID }),
                      let toIndex = appState.experiments.firstIndex(where: { $0.id == experiment.id }) else { return }
                let dest = edge == .bottom ? toIndex + 1 : toIndex
                if dest != fromIndex && dest != fromIndex + 1 {
                    DebugLog.shared.logUI("reorder experiment from \(fromIndex) to \(dest)")
                    appState.moveExperiment(from: IndexSet(integer: fromIndex), to: dest > fromIndex ? dest : dest)
                }
            }
        ))

        if isExpanded {
            // Info row
            infoRow(experiment)

            // Data Tables
            if !f.dataTables.isEmpty || searchText.isEmpty {
                sectionLabel("Data Tables")
                ForEach(f.dataTables) { table in
                    itemRow(isSelected: appState.activeItemID == table.id) {
                        selectItem(table.id, kindMap: kindMap)
                    } content: {
                        dataTableRow(table, experiment: experiment)
                    }
                    .draggable(table.id.uuidString)
                    .overlay(alignment: dropEdge == .top ? .top : .bottom) {
                        if isDragging && dropTargetID == table.id {
                            Rectangle().fill(Color.accentColor).frame(height: 2)
                        }
                    }
                    .onDrop(of: [.text], delegate: ReorderDropDelegate(
                        targetID: table.id, dropTargetID: $dropTargetID, dropEdge: $dropEdge, isDragging: $isDragging, draggedItemID: $draggedItemID, lastDropTime: $lastDropTime,
                        onDrop: { droppedID, edge in
                            guard droppedID != table.id,
                                  let fromIndex = experiment.dataTables.firstIndex(where: { $0.id == droppedID }),
                                  let toIndex = experiment.dataTables.firstIndex(where: { $0.id == table.id }) else { return }
                            let dest = edge == .bottom ? toIndex + 1 : toIndex
                            if dest != fromIndex && dest != fromIndex + 1 {
                                appState.moveDataTable(from: IndexSet(integer: fromIndex), to: dest, in: experiment.id)
                            }
                        }
                    ))
                }
                if searchText.isEmpty {
                    Button {
                        appState.activeExperimentID = experiment.id
                        DebugLog.shared.logUI("open NewDataTableDialog", detail: "experiment: \(experiment.label)")
                        showNewDataTableDialog = true
                    } label: {
                        Label("New Data Table...", systemImage: "plus")
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .padding(.leading, 36)
                    .padding(.vertical, 2)
                }
            }

            // Graphs
            if !f.graphs.isEmpty || searchText.isEmpty {
                sectionLabel("Graphs")
                ForEach(f.graphs) { graph in
                    itemRow(isSelected: appState.activeItemID == graph.id) {
                        selectItem(graph.id, kindMap: kindMap)
                    } content: {
                        graphRow(graph, experiment: experiment)
                    }
                    .draggable(graph.id.uuidString)
                    .overlay(alignment: dropEdge == .top ? .top : .bottom) {
                        if isDragging && dropTargetID == graph.id {
                            Rectangle().fill(Color.accentColor).frame(height: 2)
                        }
                    }
                    .onDrop(of: [.text], delegate: ReorderDropDelegate(
                        targetID: graph.id, dropTargetID: $dropTargetID, dropEdge: $dropEdge, isDragging: $isDragging, draggedItemID: $draggedItemID, lastDropTime: $lastDropTime,
                        onDrop: { droppedID, edge in
                            guard droppedID != graph.id,
                                  let fromIndex = experiment.graphs.firstIndex(where: { $0.id == droppedID }),
                                  let toIndex = experiment.graphs.firstIndex(where: { $0.id == graph.id }) else { return }
                            let dest = edge == .bottom ? toIndex + 1 : toIndex
                            if dest != fromIndex && dest != fromIndex + 1 {
                                appState.moveGraph(from: IndexSet(integer: fromIndex), to: dest, in: experiment.id)
                            }
                        }
                    ))
                }
                if searchText.isEmpty {
                    Button {
                        appState.activeExperimentID = experiment.id
                        DebugLog.shared.logUI("open NewGraphDialog", detail: "experiment: \(experiment.label)")
                        showNewGraphDialog = true
                    } label: {
                        Label("New Graph...", systemImage: "plus")
                            .foregroundStyle(experiment.hasData ? .secondary : .quaternary)
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .padding(.leading, 36)
                    .padding(.vertical, 2)
                    .disabled(!experiment.hasData)
                }
            }

            // Results
            if !f.analyses.isEmpty || searchText.isEmpty {
                sectionLabel("Results")
                ForEach(f.analyses) { analysis in
                    itemRow(isSelected: appState.activeItemID == analysis.id) {
                        selectItem(analysis.id, kindMap: kindMap)
                    } content: {
                        analysisRow(analysis, experiment: experiment)
                    }
                    .draggable(analysis.id.uuidString)
                    .overlay(alignment: dropEdge == .top ? .top : .bottom) {
                        if isDragging && dropTargetID == analysis.id {
                            Rectangle().fill(Color.accentColor).frame(height: 2)
                        }
                    }
                    .onDrop(of: [.text], delegate: ReorderDropDelegate(
                        targetID: analysis.id, dropTargetID: $dropTargetID, dropEdge: $dropEdge, isDragging: $isDragging, draggedItemID: $draggedItemID, lastDropTime: $lastDropTime,
                        onDrop: { droppedID, edge in
                            guard droppedID != analysis.id,
                                  let fromIndex = experiment.analyses.firstIndex(where: { $0.id == droppedID }),
                                  let toIndex = experiment.analyses.firstIndex(where: { $0.id == analysis.id }) else { return }
                            let dest = edge == .bottom ? toIndex + 1 : toIndex
                            if dest != fromIndex && dest != fromIndex + 1 {
                                appState.moveAnalysis(from: IndexSet(integer: fromIndex), to: dest, in: experiment.id)
                            }
                        }
                    ))
                }
                if searchText.isEmpty {
                    Button {
                        appState.activeExperimentID = experiment.id
                        DebugLog.shared.logUI("open AnalyzeDialog", detail: "experiment: \(experiment.label)")
                        showAnalyzeDialog = true
                    } label: {
                        Label("New Analysis...", systemImage: "plus")
                            .foregroundStyle(experiment.hasData ? .secondary : .quaternary)
                            .font(.caption)
                    }
                    .buttonStyle(.plain)
                    .padding(.leading, 36)
                    .padding(.vertical, 2)
                    .disabled(!experiment.hasData)
                }
            }

            Divider()
                .padding(.vertical, 4)
        }
    }

    // MARK: - Reusable row with selection highlight

    private func itemRow<Content: View>(isSelected: Bool, action: @escaping () -> Void, @ViewBuilder content: () -> Content) -> some View {
        Button(action: action) {
            content()
                .padding(.horizontal, 12)
                .padding(.leading, 20)
                .padding(.vertical, 3)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(isSelected ? Color.accentColor.opacity(0.2) : Color.clear)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private func sectionLabel(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(.tertiary)
            .textCase(.uppercase)
            .padding(.leading, 28)
            .padding(.top, 6)
            .padding(.bottom, 2)
    }

    // MARK: - Experiment Header

    private func experimentHeader(_ experiment: Experiment) -> some View {
        HStack {
            Image(systemName: "flask")
                .foregroundStyle(.secondary)
            if editingID == experiment.id {
                TextField("Name", text: Bindable(experiment).label)
                    .textFieldStyle(.plain)
                    .fontWeight(.semibold)
                    .onSubmit { editingID = nil }
            } else {
                Text(experiment.label)
                    .fontWeight(.semibold)
                    .lineLimit(1)
            }
            Spacer()
            Button {
                experimentToDelete = experiment
            } label: {
                Image(systemName: "xmark.circle")
                    .foregroundStyle(.tertiary)
            }
            .buttonStyle(.plain)
        }
        .contextMenu {
            Button("Rename") {
                DebugLog.shared.logUI("rename experiment: \(experiment.label)")
                editingID = experiment.id
            }
            Button("Delete", role: .destructive) {
                DebugLog.shared.logUI("delete experiment: \(experiment.label)")
                experimentToDelete = experiment
            }
        }
    }

    // MARK: - Info Row

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        return f
    }()

    private func infoRow(_ experiment: Experiment) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if !experiment.description.isEmpty {
                Text(experiment.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            HStack(spacing: 4) {
                Image(systemName: "clock")
                    .font(.system(size: 8))
                    .foregroundStyle(.tertiary)
                Text("Created \(Self.dateFormatter.string(from: experiment.createdAt))")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
            }
            HStack(spacing: 4) {
                Image(systemName: "pencil")
                    .font(.system(size: 8))
                    .foregroundStyle(.tertiary)
                Text("Modified \(Self.dateFormatter.string(from: experiment.lastModifiedAt))")
                    .font(.system(size: 9))
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.leading, 16)
        .padding(.vertical, 4)
    }

    // MARK: - Row Views

    private func dataTableRow(_ table: DataTable, experiment: Experiment) -> some View {
        Label {
            if editingID == table.id {
                TextField("Name", text: Bindable(table).label)
                    .textFieldStyle(.plain)
                    .onSubmit { editingID = nil }
            } else {
                HStack {
                    Text(table.label)
                        .lineLimit(1)
                    Text("(\(table.tableType.label))")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
        } icon: {
            Image(systemName: table.sfSymbol)
                .foregroundStyle(.secondary)
        }
        .contextMenu {
            Button("Rename") { editingID = table.id }
            if experiment.dataTables.count > 1 {
                Button("Delete", role: .destructive) {
                    appState.removeDataTable(id: table.id)
                }
            }
        }
    }

    private func graphRow(_ graph: Graph, experiment: Experiment) -> some View {
        let tableName = experiment.dataTable(for: graph)?.label ?? "—"
        return Label {
            if editingID == graph.id {
                TextField("Name", text: Bindable(graph).label)
                    .textFieldStyle(.plain)
                    .onSubmit { editingID = nil }
            } else {
                HStack {
                    Text(graph.label)
                        .lineLimit(1)
                    Text("→ \(tableName)")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
        } icon: {
            Image(systemName: graph.chartType.sfSymbol)
                .foregroundStyle(.blue)
        }
        .contextMenu {
            Button("Rename") { editingID = graph.id }
            Button("Delete", role: .destructive) {
                appState.removeGraph(id: graph.id)
            }
        }
    }

    private func analysisRow(_ analysis: Analysis, experiment: Experiment) -> some View {
        let tableName = experiment.dataTable(for: analysis)?.label ?? "—"
        return Label {
            if editingID == analysis.id {
                TextField("Name", text: Bindable(analysis).label)
                    .textFieldStyle(.plain)
                    .onSubmit { editingID = nil }
            } else {
                HStack {
                    Text(analysis.label)
                        .lineLimit(1)
                    Text("→ \(tableName)")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
        } icon: {
            Image(systemName: "list.clipboard")
                .foregroundStyle(.orange)
        }
        .contextMenu {
            Button("Rename") { editingID = analysis.id }
            Button("Delete", role: .destructive) {
                appState.removeAnalysis(id: analysis.id)
            }
        }
    }
}

// MARK: - Reorder Drop Delegate

/// Drop delegate that tracks cursor position within a row to show a
/// top or bottom insertion indicator, then calls back with the resolved edge.
struct ReorderDropDelegate: DropDelegate {
    let targetID: UUID
    @Binding var dropTargetID: UUID?
    @Binding var dropEdge: NavigatorView.DropEdge
    @Binding var isDragging: Bool
    @Binding var draggedItemID: UUID?
    /// Timestamp when a drop was last completed. Any callbacks within 500ms are ignored.
    @Binding var lastDropTime: Date?
    let onDrop: (UUID, NavigatorView.DropEdge) -> Void

    /// Whether we're in the post-drop ignore window (macOS sends spurious callbacks after performDrop).
    private var isInPostDropWindow: Bool {
        if let t = lastDropTime { return Date().timeIntervalSince(t) < 0.5 }
        return false
    }

    func dropEntered(info: DropInfo) {
        guard !isInPostDropWindow else { return }
        isDragging = true
        dropTargetID = targetID
        // Cache the dragged item ID on first enter so performDrop can use it synchronously
        if draggedItemID == nil {
            if let item = info.itemProviders(for: [.text]).first {
                item.loadItem(forTypeIdentifier: "public.text", options: nil) { data, _ in
                    guard let data = data as? Data,
                          let str = String(data: data, encoding: .utf8),
                          let uuid = UUID(uuidString: str) else { return }
                    DispatchQueue.main.async { self.draggedItemID = uuid }
                }
            }
        }
    }

    func dropUpdated(info: DropInfo) -> DropProposal? {
        guard !isInPostDropWindow else { return DropProposal(operation: .move) }
        dropTargetID = targetID
        dropEdge = info.location.y < 12 ? .top : .bottom
        return DropProposal(operation: .move)
    }

    func dropExited(info: DropInfo) {
        if dropTargetID == targetID {
            dropTargetID = nil
        }
    }

    func performDrop(info: DropInfo) -> Bool {
        let savedEdge = dropEdge
        isDragging = false
        dropTargetID = nil
        lastDropTime = Date()
        // Use the cached ID for instant reorder — no async delay
        if let droppedID = draggedItemID {
            draggedItemID = nil
            onDrop(droppedID, savedEdge)
            return true
        }
        // Fallback: async load (shouldn't normally hit this path)
        draggedItemID = nil
        guard let item = info.itemProviders(for: [.text]).first else { return false }
        item.loadItem(forTypeIdentifier: "public.text", options: nil) { data, _ in
            guard let data = data as? Data,
                  let str = String(data: data, encoding: .utf8),
                  let droppedID = UUID(uuidString: str) else { return }
            DispatchQueue.main.async {
                self.onDrop(droppedID, savedEdge)
            }
        }
        return true
    }

    func validateDrop(info: DropInfo) -> Bool {
        true
    }
}

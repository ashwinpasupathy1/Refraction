// Experiment.swift — Top-level container for related data, graphs, and analyses.
// An experiment owns multiple DataTables. Each Graph/Analysis links to one DataTable.

import Foundation

/// The kind of item selected in the navigator.
enum ItemKind: String {
    case dataTable
    case graph
    case analysis
}

@Observable
final class Experiment: Identifiable {
    let id: UUID
    var label: String
    var description: String
    var dataTables: [DataTable]
    var graphs: [Graph]
    var analyses: [Analysis]
    var info: String
    var createdAt: Date
    var lastModifiedAt: Date

    init(
        id: UUID = UUID(),
        label: String,
        description: String = "",
        dataTables: [DataTable]? = nil,
        graphs: [Graph] = [],
        analyses: [Analysis] = [],
        info: String = "",
        createdAt: Date = Date(),
        lastModifiedAt: Date = Date()
    ) {
        self.id = id
        self.label = label
        self.description = description
        self.dataTables = dataTables ?? []
        self.graphs = graphs
        self.analyses = analyses
        self.info = info
        self.createdAt = createdAt
        self.lastModifiedAt = lastModifiedAt
    }

    /// Create a new empty experiment (no default data table).
    static func new(label: String) -> Experiment {
        Experiment(label: label)
    }

    // MARK: - Data Table management

    @discardableResult
    func addDataTable(type: TableType, label: String? = nil) -> DataTable {
        let name = label ?? "\(type.label) \(dataTables.count + 1)"
        let table = DataTable(label: name, tableType: type)
        dataTables.append(table)
        return table
    }

    func removeDataTable(id: UUID) {
        dataTables.removeAll { $0.id == id }
        // Orphaned graphs/analyses that linked to this table keep their dataTableID
        // but will show "missing data table" in the UI until re-linked.
    }

    // MARK: - Graph management

    /// Whether a graph with this label already exists in the experiment.
    func hasGraphNamed(_ label: String) -> Bool {
        graphs.contains { $0.label == label }
    }

    @discardableResult
    func addGraph(chartType: ChartType, dataTableID: UUID, label: String? = nil) -> Graph? {
        let name = label ?? chartType.label
        // Reject duplicate names
        guard !hasGraphNamed(name) else { return nil }
        let graph = Graph(label: name, dataTableID: dataTableID, chartType: chartType)
        graphs.append(graph)
        return graph
    }

    func removeGraph(id: UUID) {
        graphs.removeAll { $0.id == id }
    }

    // MARK: - Analysis management

    @discardableResult
    func addAnalysis(dataTableID: UUID, label: String = "Results", analysisType: String = "") -> Analysis {
        let analysis = Analysis(label: label, dataTableID: dataTableID, analysisType: analysisType)
        analyses.append(analysis)
        return analysis
    }

    func removeAnalysis(id: UUID) {
        analyses.removeAll { $0.id == id }
    }

    // MARK: - Reorder

    func moveDataTable(from source: IndexSet, to destination: Int) {
        dataTables.move(fromOffsets: source, toOffset: destination)
    }

    func moveGraph(from source: IndexSet, to destination: Int) {
        graphs.move(fromOffsets: source, toOffset: destination)
    }

    func moveAnalysis(from source: IndexSet, to destination: Int) {
        analyses.move(fromOffsets: source, toOffset: destination)
    }

    // MARK: - Lookups

    /// Find the DataTable for a given graph.
    func dataTable(for graph: Graph) -> DataTable? {
        dataTables.first { $0.id == graph.dataTableID }
    }

    /// Find the DataTable for a given analysis.
    func dataTable(for analysis: Analysis) -> DataTable? {
        dataTables.first { $0.id == analysis.dataTableID }
    }

    /// All chart types valid across any data table in this experiment.
    var allValidChartTypes: [ChartType] {
        let types = Set(dataTables.flatMap { $0.tableType.validChartTypes })
        return ChartType.allCases.filter { types.contains($0) }
    }

    /// Chart types valid for a specific data table.
    func validChartTypes(for dataTableID: UUID) -> [ChartType] {
        dataTables.first { $0.id == dataTableID }?.tableType.validChartTypes ?? []
    }

    /// Whether any data table has data loaded.
    var hasData: Bool {
        dataTables.contains { $0.hasData }
    }
}

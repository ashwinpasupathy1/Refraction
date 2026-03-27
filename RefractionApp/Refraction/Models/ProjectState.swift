// ProjectState.swift — Lightweight Codable snapshot of the navigator tree.
// Persisted to ~/.refraction/project.json for session restore.

import Foundation

struct ProjectState: Codable {
    var experiments: [ExperimentState]
    var activeExperimentID: String?
    var activeItemID: String?
    var activeItemKind: String?

    struct ExperimentState: Codable {
        var id: String
        var label: String
        var dataTables: [DataTableState]
        var graphs: [GraphState]
        var analyses: [AnalysisState]
    }

    struct DataTableState: Codable {
        var id: String
        var label: String
        var tableType: String
        var originalFileName: String?
        var columns: [String]?
        var rows: [[CellValue]]?
    }

    struct GraphState: Codable {
        var id: String
        var label: String
        var dataTableID: String
        var chartType: String
    }

    struct AnalysisState: Codable {
        var id: String
        var label: String
        var dataTableID: String
        var analysisType: String
        var notes: String?
    }

    // MARK: - Persistence path

    static var projectFileURL: URL {
        let dir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".refraction", isDirectory: true)
        return dir.appendingPathComponent("project.json")
    }

    func writeToDisk() {
        let dir = Self.projectFileURL.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        guard let data = try? encoder.encode(self) else { return }
        try? data.write(to: Self.projectFileURL, options: .atomic)
    }

    static func readFromDisk() -> ProjectState? {
        guard let data = try? Data(contentsOf: projectFileURL) else { return nil }
        return try? JSONDecoder().decode(ProjectState.self, from: data)
    }
}

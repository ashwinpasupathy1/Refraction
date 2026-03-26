// AppState.swift — Central observable state for the Refraction app.
// Manages experiments, each containing data tables, graphs, and analyses.

import AppKit
import Foundation
import RefractionRenderer
import UniformTypeIdentifiers

// MARK: - Recent Files Manager

@Observable
final class RecentFiles {
    private static let key = "recentProjectPaths"
    private static let maxCount = 10

    var paths: [URL] {
        didSet { save() }
    }

    static let shared = RecentFiles()

    private init() {
        let saved = UserDefaults.standard.stringArray(forKey: Self.key) ?? []
        paths = saved.compactMap { URL(fileURLWithPath: $0) }
    }

    func add(_ url: URL) {
        paths.removeAll { $0 == url }
        paths.insert(url, at: 0)
        if paths.count > Self.maxCount {
            paths = Array(paths.prefix(Self.maxCount))
        }
    }

    func clear() {
        paths = []
    }

    private func save() {
        UserDefaults.standard.set(paths.map(\.path), forKey: Self.key)
    }
}

@Observable
final class AppState {

    // MARK: - Undo Manager

    let undoManager = UndoManager()

    /// Whether undo is available.
    var canUndo: Bool { undoManager.canUndo }
    /// Whether redo is available.
    var canRedo: Bool { undoManager.canRedo }

    // MARK: - Experiment state

    /// All experiments in the project.
    var experiments: [Experiment] = []

    /// Currently selected experiment ID.
    var activeExperimentID: UUID?

    /// Currently selected item ID (could be a DataTable, Graph, or Analysis).
    var activeItemID: UUID?

    /// Kind of the currently selected item.
    var activeItemKind: ItemKind?

    /// Developer mode: show raw JSON from the engine for debugging.
    var developerMode: Bool = false

    /// Current project file path (nil = never saved).
    var projectFilePath: URL?

    /// Whether the project has unsaved changes.
    var hasUnsavedChanges: Bool = false

    /// The display name for untitled projects (e.g. "Untitled.refract").
    private var untitledName: String = "Untitled.refract"

    /// Tracks which "Untitled N" numbers are currently in use (0 = "Untitled").
    private static var activeUntitledNumbers: Set<Int> = [0]

    /// Tracks file paths of all currently open projects to prevent duplicates.
    private static var openProjectPaths: Set<String> = []

    /// Display name for the title bar.
    var projectDisplayName: String {
        if let path = projectFilePath {
            let name = path.lastPathComponent  // keep .refract extension
            return hasUnsavedChanges ? "\(name) — Edited" : name
        }
        return hasUnsavedChanges ? "\(untitledName) — Edited" : untitledName
    }

    private var currentUntitledNumber: Int? {
        guard projectFilePath == nil else { return nil }
        if untitledName == "Untitled.refract" { return 0 }
        let prefix = "Untitled "
        let suffix = ".refract"
        guard untitledName.hasPrefix(prefix) && untitledName.hasSuffix(suffix) else { return nil }
        let middle = untitledName.dropFirst(prefix.count).dropLast(suffix.count)
        return Int(middle)
    }

    private static func nextUntitledNumber() -> Int {
        var n = 0
        while activeUntitledNumbers.contains(n) { n += 1 }
        return n
    }

    private static func untitledNameFor(_ n: Int) -> String {
        n == 0 ? "Untitled.refract" : "Untitled \(n).refract"
    }

    /// Whether any render request is in flight.
    var isLoading: Bool = false

    /// Most recent error message (nil = no error).
    var error: String?

    // MARK: - Computed properties

    /// The active experiment.
    var activeExperiment: Experiment? {
        experiments.first { $0.id == activeExperimentID }
    }

    /// The active graph (if a graph is selected).
    var activeGraph: Graph? {
        guard activeItemKind == .graph, let id = activeItemID else { return nil }
        return activeExperiment?.graphs.first { $0.id == id }
    }

    /// The active data table (if a data table is selected).
    var activeDataTable: DataTable? {
        guard activeItemKind == .dataTable, let id = activeItemID else { return nil }
        return activeExperiment?.dataTables.first { $0.id == id }
    }

    /// The active analysis (if an analysis is selected).
    var activeAnalysis: Analysis? {
        guard activeItemKind == .analysis, let id = activeItemID else { return nil }
        return activeExperiment?.analyses.first { $0.id == id }
    }

    /// The data table linked to the active graph.
    var activeGraphDataTable: DataTable? {
        guard let graph = activeGraph else { return nil }
        return activeExperiment?.dataTable(for: graph)
    }

    /// Whether any experiment exists.
    var hasExperiments: Bool {
        !experiments.isEmpty
    }

    // MARK: - Experiment Management

    /// Add a new experiment and select it.
    @discardableResult
    func addExperiment(label: String? = nil) -> Experiment {
        let name = label ?? "Experiment \(experiments.count + 1)"
        DebugLog.shared.logAppEvent("addExperiment(\"\(name)\")")
        let experiment = Experiment.new(label: name)
        experiments.append(experiment)
        activeExperimentID = experiment.id
        if let first = experiment.dataTables.first {
            activeItemID = first.id
            activeItemKind = .dataTable
        }
        markDirty()

        // Register undo
        let expID = experiment.id
        undoManager.registerUndo(withTarget: self) { target in
            target.removeExperiment(id: expID)
        }
        undoManager.setActionName("Add Experiment")

        return experiment
    }

    /// Remove an experiment.
    func removeExperiment(id: UUID) {
        guard let index = experiments.firstIndex(where: { $0.id == id }) else { return }
        let removed = experiments[index]
        experiments.remove(at: index)
        markDirty()
        if activeExperimentID == id {
            activeExperimentID = experiments.first?.id
            activeItemID = experiments.first?.dataTables.first?.id
            activeItemKind = experiments.first != nil ? .dataTable : nil
        }

        // Register undo: re-insert the experiment
        undoManager.registerUndo(withTarget: self) { target in
            target.experiments.insert(removed, at: min(index, target.experiments.count))
            target.activeExperimentID = removed.id
            target.markDirty()
        }
        undoManager.setActionName("Remove Experiment")
    }

    // MARK: - Data Table Management

    /// Add a data table to the active experiment.
    @discardableResult
    func addDataTable(type: TableType, label: String? = nil) -> DataTable? {
        guard let experiment = activeExperiment else { return nil }
        DebugLog.shared.logAppEvent("addDataTable(type: \(type.rawValue), label: \(label ?? "nil"))")
        let table = experiment.addDataTable(type: type, label: label)
        activeItemID = table.id
        activeItemKind = .dataTable
        markDirty()

        let tableID = table.id
        let expID = experiment.id
        undoManager.registerUndo(withTarget: self) { target in
            target.removeDataTable(id: tableID)
        }
        undoManager.setActionName("Add Data Table")

        return table
    }

    /// Remove a data table from the active experiment.
    func removeDataTable(id: UUID) {
        guard let experiment = activeExperiment,
              let index = experiment.dataTables.firstIndex(where: { $0.id == id }) else { return }
        let removed = experiment.dataTables[index]
        experiment.removeDataTable(id: id)
        markDirty()
        if activeItemID == id {
            activeItemID = experiment.dataTables.first?.id
            activeItemKind = experiment.dataTables.first != nil ? .dataTable : nil
        }

        let expID = experiment.id
        undoManager.registerUndo(withTarget: self) { target in
            if let exp = target.experiments.first(where: { $0.id == expID }) {
                exp.dataTables.insert(removed, at: min(index, exp.dataTables.count))
                target.activeItemID = removed.id
                target.activeItemKind = .dataTable
                target.markDirty()
            }
        }
        undoManager.setActionName("Remove Data Table")
    }

    // MARK: - Graph Management

    /// Add a graph to the active experiment, linked to a specific data table.
    /// Returns nil if a graph with that name already exists.
    @discardableResult
    func addGraph(chartType: ChartType, dataTableID: UUID, label: String? = nil) -> Graph? {
        guard let experiment = activeExperiment else { return nil }
        DebugLog.shared.logAppEvent("addGraph(chartType: \(chartType.rawValue), label: \(label ?? "auto"), dataTableID: \(dataTableID.uuidString.prefix(8)))")
        guard let graph = experiment.addGraph(chartType: chartType, dataTableID: dataTableID, label: label) else {
            return nil
        }
        activeItemID = graph.id
        activeItemKind = .graph
        markDirty()
        // Auto-generate the chart
        Task { @MainActor in
            await generatePlot()
        }
        return graph
    }

    /// Remove a graph from the active experiment.
    func removeGraph(id: UUID) {
        guard let experiment = activeExperiment,
              let index = experiment.graphs.firstIndex(where: { $0.id == id }) else { return }
        let removed = experiment.graphs[index]
        experiment.removeGraph(id: id)
        markDirty()
        if activeItemID == id {
            activeItemID = experiment.dataTables.first?.id
            activeItemKind = .dataTable
        }

        let expID = experiment.id
        undoManager.registerUndo(withTarget: self) { target in
            if let exp = target.experiments.first(where: { $0.id == expID }) {
                exp.graphs.insert(removed, at: min(index, exp.graphs.count))
                target.activeItemID = removed.id
                target.activeItemKind = .graph
                target.markDirty()
            }
        }
        undoManager.setActionName("Remove Graph")
    }

    // MARK: - Analysis Management

    /// Add an analysis to the active experiment, linked to a specific data table.
    @discardableResult
    func addAnalysis(dataTableID: UUID, label: String = "Results", analysisType: String = "") -> Analysis? {
        guard let experiment = activeExperiment else { return nil }
        let analysis = experiment.addAnalysis(dataTableID: dataTableID, label: label, analysisType: analysisType)
        activeItemID = analysis.id
        activeItemKind = .analysis
        markDirty()
        return analysis
    }

    /// Remove an analysis from the active experiment.
    func removeAnalysis(id: UUID) {
        guard let experiment = activeExperiment else { return }
        experiment.removeAnalysis(id: id)
        markDirty()
        if activeItemID == id {
            activeItemID = experiment.dataTables.first?.id
            activeItemKind = .dataTable
        }
    }

    // MARK: - Selection

    /// Select an item in the navigator. Searches all experiments to find it.
    func selectItem(_ itemID: UUID, kind: ItemKind) {
        for experiment in experiments {
            let found: Bool
            switch kind {
            case .dataTable:
                found = experiment.dataTables.contains { $0.id == itemID }
            case .graph:
                found = experiment.graphs.contains { $0.id == itemID }
            case .analysis:
                found = experiment.analyses.contains { $0.id == itemID }
            }
            if found {
                activeExperimentID = experiment.id
                activeItemID = itemID
                activeItemKind = kind
                return
            }
        }
    }

    // MARK: - File Loading

    /// Upload a file and associate it with the specified data table in the active experiment.
    @MainActor
    func uploadFile(url: URL, for dataTable: DataTable? = nil) async {
        DebugLog.shared.logAppEvent("uploadFile(\(url.lastPathComponent))", detail: "path: \(url.path)")
        let table: DataTable?
        if let dt = dataTable {
            table = dt
        } else if activeItemKind == .dataTable {
            table = activeDataTable
        } else if let graph = activeGraph {
            table = activeExperiment?.dataTable(for: graph)
        } else {
            table = activeExperiment?.dataTables.first
        }
        guard let table else { return }

        do {
            let serverPath = try await APIClient.shared.upload(fileURL: url)
            table.dataFilePath = serverPath
            table.originalFileName = url.lastPathComponent
            // Update all graphs linked to this table
            if let experiment = activeExperiment {
                for graph in experiment.graphs where graph.dataTableID == table.id {
                    graph.chartConfig.excelPath = serverPath
                }
            }
        } catch let apiError as APIError {
            self.error = "File upload failed: \(apiError.localizedDescription)"
        } catch {
            self.error = "File upload failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Chart Generation

    /// Generate the chart for the active graph.
    @MainActor
    func generatePlot() async {
        guard let experiment = activeExperiment,
              let graph = activeGraph else {
            error = "Select a graph first."
            return
        }
        DebugLog.shared.logAppEvent("generatePlot(\(graph.chartType.rawValue))", detail: "graph: \(graph.label), table: \(experiment.dataTable(for: graph)?.label ?? "none")")

        guard let table = experiment.dataTable(for: graph),
              let dataPath = table.dataFilePath, !dataPath.isEmpty else {
            error = "No data file loaded. Import data into the data table first."
            return
        }

        // Ensure the config has the correct data path
        graph.chartConfig.excelPath = dataPath

        // Don't block UI — only set loading on the specific graph, not globally
        graph.isLoading = true
        error = nil

        do {
            let (spec, rawJSON) = try await APIClient.shared.analyzeWithRawJSON(
                chartType: graph.chartType,
                config: graph.chartConfig,
                debug: developerMode
            )
            graph.chartSpec = spec
            graph.rawJSON = rawJSON
            self.error = nil
        } catch {
            // Single retry after a short delay (server may be starting)
            do {
                try await Task.sleep(for: .milliseconds(500))
                let (spec, rawJSON) = try await APIClient.shared.analyzeWithRawJSON(
                    chartType: graph.chartType,
                    config: graph.chartConfig,
                    debug: developerMode
                )
                graph.chartSpec = spec
                graph.rawJSON = rawJSON
                self.error = nil
            } catch {
                self.error = "Analysis failed: \(error.localizedDescription)"
                graph.chartSpec = nil
            }
        }

        graph.isLoading = false
    }

    // MARK: - Statistical Analysis

    /// Run a standalone statistical analysis and create an Analysis item.
    @MainActor
    func runAnalysis(analysisType: String, dataTableID: UUID? = nil, label: String? = nil) async {
        guard let experiment = activeExperiment else {
            error = "No active experiment."
            return
        }

        let tableID = dataTableID ?? activeDataTable?.id ?? experiment.dataTables.first?.id
        guard let tableID,
              let table = experiment.dataTables.first(where: { $0.id == tableID }),
              let dataPath = table.dataFilePath, !dataPath.isEmpty else {
            error = "No data file loaded. Import data first."
            return
        }

        isLoading = true
        error = nil

        do {
            let response = try await APIClient.shared.analyzeStats(
                excelPath: dataPath,
                analysisType: analysisType
            )

            guard response.ok else {
                error = response.error ?? "Analysis failed."
                isLoading = false
                return
            }

            let effectiveLabel = label ?? response.analysisLabel ?? analysisType
            guard let analysis = addAnalysis(dataTableID: tableID, label: effectiveLabel, analysisType: analysisType) else {
                isLoading = false
                return
            }

            analysis.rawJSON = response.rawJSON

            // Build summary notes
            var notes = "# \(effectiveLabel)\n\n"
            if let summary = response.summary {
                notes += "## Summary\n\(summary)\n\n"
            }
            if let descriptive = response.descriptive {
                notes += "## Descriptive Statistics\n"
                for group in descriptive {
                    let name = group["group"]?.displayString ?? "—"
                    let n = group["n"]?.displayString ?? "—"
                    let mean = group["mean"]?.displayString ?? "—"
                    let sd = group["sd"]?.displayString ?? "—"
                    let sem = group["sem"]?.displayString ?? "—"
                    notes += "  \(name): n=\(n), mean=\(mean), SD=\(sd), SEM=\(sem)\n"
                }
                notes += "\n"
            }
            if let comparisons = response.comparisons, !comparisons.isEmpty {
                notes += "## Comparisons\n"
                for comp in comparisons {
                    let ga = comp["group_a"]?.displayString ?? "—"
                    let gb = comp["group_b"]?.displayString ?? "—"
                    let p = comp["p_value"]?.displayString ?? "—"
                    let stars = comp["stars"]?.displayString ?? ""
                    notes += "  \(ga) vs \(gb): p = \(p) \(stars)\n"
                }
                notes += "\n"
            }
            if let rec = response.recommendation {
                notes += "## Recommendation\n"
                notes += "  \(rec.testLabel): \(rec.justification)\n"
            }
            analysis.notes = notes
        } catch {
            self.error = "Analysis failed: \(error.localizedDescription)"
        }

        isLoading = false
    }

    // MARK: - New Project

    func newProject() {
        DebugLog.shared.logAppEvent("newProject()")
        if let n = currentUntitledNumber {
            Self.activeUntitledNumbers.remove(n)
        }
        if let oldPath = projectFilePath {
            Self.openProjectPaths.remove(oldPath.standardizedFileURL.path)
        }
        let n = Self.nextUntitledNumber()
        Self.activeUntitledNumbers.insert(n)
        untitledName = Self.untitledNameFor(n)

        experiments = []
        activeExperimentID = nil
        activeItemID = nil
        activeItemKind = nil
        projectFilePath = nil
        hasUnsavedChanges = false
        error = nil
    }

    // MARK: - Open .refract File

    @MainActor
    func openProjectFile() async {
        DebugLog.shared.logAppEvent("openProjectFile()")
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            .init(filenameExtension: "refract") ?? .data
        ]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.message = "Select a Refraction project file"
        panel.title = "Open Project"

        guard panel.runModal() == .OK, let url = panel.url else { return }

        let resolvedPath = url.standardizedFileURL.path
        if Self.openProjectPaths.contains(resolvedPath) {
            error = "\(url.lastPathComponent) is already open."
            return
        }

        await loadProjectFromURL(url)
    }

    @MainActor
    func loadProjectFromURL(_ url: URL) async {
        DebugLog.shared.logAppEvent("loadProjectFromURL(\(url.lastPathComponent))")
        isLoading = true
        error = nil

        do {
            // Read the ZIP client-side — no server round-trip for metadata
            let zipData = try Data(contentsOf: url)
            let tempDir = FileManager.default.temporaryDirectory
                .appendingPathComponent("refraction_\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)

            // Unzip using Foundation (Archive utility)
            let zipURL = tempDir.appendingPathComponent("archive.refract")
            try zipData.write(to: zipURL)

            // Use Process to unzip (Foundation has no built-in ZIP reader)
            let unzipDir = tempDir.appendingPathComponent("contents")
            try FileManager.default.createDirectory(at: unzipDir, withIntermediateDirectories: true)
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
            process.arguments = ["-o", zipURL.path, "-d", unzipDir.path]
            process.standardOutput = FileHandle.nullDevice
            process.standardError = FileHandle.nullDevice
            try process.run()
            process.waitUntilExit()

            guard process.terminationStatus == 0 else {
                throw NSError(domain: "Refraction", code: 1, userInfo: [NSLocalizedDescriptionKey: "Failed to unzip project file"])
            }

            // Parse project.json
            let projectURL = unzipDir.appendingPathComponent("project.json")
            let projectData = try Data(contentsOf: projectURL)
            guard var project = try JSONSerialization.jsonObject(with: projectData) as? [String: Any] else {
                throw NSError(domain: "Refraction", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid project.json"])
            }

            // Upload embedded CSV data files to the server so the engine can access them,
            // validate each against its declared table type, and replace dataRef with server-side path
            var validationWarnings: [String] = []
            if var experiments = project["experiments"] as? [[String: Any]] {
                for i in 0..<experiments.count {
                    let expLabel = experiments[i]["label"] as? String ?? "Experiment \(i+1)"
                    if var tables = experiments[i]["dataTables"] as? [[String: Any]] {
                        for j in 0..<tables.count {
                            let tableLabel = tables[j]["label"] as? String ?? "Table \(j+1)"
                            let tableType = tables[j]["tableType"] as? String ?? "column"

                            if let dataRef = tables[j]["dataRef"] as? String, !dataRef.isEmpty {
                                let csvURL = unzipDir.appendingPathComponent(dataRef)
                                if FileManager.default.fileExists(atPath: csvURL.path) {
                                    DebugLog.shared.logAppEvent("uploading embedded data: \(dataRef)")
                                    let serverPath = try await APIClient.shared.upload(fileURL: csvURL)
                                    tables[j]["dataFilePath"] = serverPath

                                    // Validate the data against the declared table type
                                    DebugLog.shared.logAppEvent("validating \(tableLabel) as \(tableType)")
                                    do {
                                        let validation = try await APIClient.shared.validateTable(
                                            excelPath: serverPath,
                                            tableType: tableType
                                        )
                                        if validation.valid == false {
                                            let errors = (validation.errors ?? []).joined(separator: "; ")
                                            validationWarnings.append("\(expLabel) → \(tableLabel): \(errors)")
                                            DebugLog.shared.logError(
                                                method: "APP", path: "loadValidation",
                                                error: "\(tableLabel) failed validation: \(errors)"
                                            )
                                        } else {
                                            DebugLog.shared.logAppEvent("  \(tableLabel) validated OK")
                                        }
                                    } catch {
                                        // Non-fatal: log but continue loading
                                        DebugLog.shared.logAppEvent("  \(tableLabel) validation skipped: \(error.localizedDescription)")
                                    }
                                } else {
                                    validationWarnings.append("\(expLabel) → \(tableLabel): embedded data file missing (\(dataRef))")
                                }
                            }
                            tables[j].removeValue(forKey: "dataRef")
                        }
                        experiments[i]["dataTables"] = tables
                    }
                }
                project["experiments"] = experiments
            }

            // Clean up temp files
            try? FileManager.default.removeItem(at: tempDir)

            // Restore state
            if let n = currentUntitledNumber {
                Self.activeUntitledNumbers.remove(n)
            }
            if let oldPath = projectFilePath {
                Self.openProjectPaths.remove(oldPath.standardizedFileURL.path)
            }

            restoreProjectFromDict(project)
            projectFilePath = url
            hasUnsavedChanges = false
            RecentFiles.shared.add(url)

            Self.openProjectPaths.insert(url.standardizedFileURL.path)
            DebugLog.shared.logAppEvent("project loaded: \(experiments.count) experiments")

            // Show validation warnings if any data tables had issues
            if !validationWarnings.isEmpty {
                self.error = "Project loaded with validation warnings:\n" + validationWarnings.joined(separator: "\n")
            }
        } catch {
            self.error = "Failed to open project: \(error.localizedDescription)"
            DebugLog.shared.logError(method: "APP", path: "loadProjectFromURL", error: error.localizedDescription)
        }

        isLoading = false
    }

    /// Restore project state from a loaded project dict.
    private func restoreProjectFromDict(_ project: [String: Any]) {
        // Try new experiment-based format first
        if let experimentsArray = project["experiments"] as? [[String: Any]] {
            restoreExperiments(experimentsArray)
            activeExperimentID = (project["activeExperimentID"] as? String).flatMap { UUID(uuidString: $0) }
                ?? experiments.first?.id
            activeItemID = (project["activeItemID"] as? String).flatMap { UUID(uuidString: $0) }
                ?? experiments.first?.dataTables.first?.id
            activeItemKind = (project["activeItemKind"] as? String).flatMap { ItemKind(rawValue: $0) }
                ?? .dataTable
            return
        }

        // Fall back to legacy dataTables format for backward compatibility
        if let tablesArray = project["dataTables"] as? [[String: Any]] {
            restoreLegacyProject(tablesArray, project: project)
            return
        }

        error = "Invalid project file."
    }

    private func restoreExperiments(_ experimentsArray: [[String: Any]]) {
        var restored: [Experiment] = []
        for expDict in experimentsArray {
            guard let idStr = expDict["id"] as? String,
                  let expID = UUID(uuidString: idStr) else { continue }
            let label = expDict["label"] as? String ?? "Experiment"
            let info = expDict["info"] as? String ?? ""

            // Data tables
            var tables: [DataTable] = []
            if let tablesArr = expDict["dataTables"] as? [[String: Any]] {
                for td in tablesArr {
                    guard let tid = (td["id"] as? String).flatMap({ UUID(uuidString: $0) }),
                          let tt = (td["tableType"] as? String).flatMap({ TableType(rawValue: $0) }) else { continue }
                    let table = DataTable(id: tid, label: td["label"] as? String ?? "", tableType: tt, dataFilePath: td["dataFilePath"] as? String, originalFileName: td["originalFileName"] as? String)
                    tables.append(table)
                }
            }

            // Graphs
            var graphs: [Graph] = []
            if let graphsArr = expDict["graphs"] as? [[String: Any]] {
                for gd in graphsArr {
                    guard let gid = (gd["id"] as? String).flatMap({ UUID(uuidString: $0) }),
                          let dtid = (gd["dataTableID"] as? String).flatMap({ UUID(uuidString: $0) }),
                          let ct = (gd["chartType"] as? String).flatMap({ ChartType(rawValue: $0) }) else { continue }
                    let graph = Graph(id: gid, label: gd["label"] as? String ?? "", dataTableID: dtid, chartType: ct)
                    if let configDict = gd["chartConfig"] as? [String: Any] {
                        graph.chartConfig.loadFromDict(configDict)
                    }
                    if let fgDict = gd["formatSettings"] as? [String: Any],
                       let fgData = try? JSONSerialization.data(withJSONObject: fgDict),
                       let fg = try? JSONDecoder().decode(FormatGraphSettings.self, from: fgData) {
                        graph.formatSettings = fg
                    }
                    if let faDict = gd["formatAxesSettings"] as? [String: Any],
                       let faData = try? JSONSerialization.data(withJSONObject: faDict),
                       let fa = try? JSONDecoder().decode(FormatAxesSettings.self, from: faData) {
                        graph.formatAxesSettings = fa
                    }
                    if let rs = (gd["renderStyle"] as? String).flatMap({ RenderStyle(rawValue: $0) }) {
                        graph.renderStyle = rs
                    }
                    // Set data path from linked table
                    if let table = tables.first(where: { $0.id == dtid }) {
                        graph.chartConfig.excelPath = table.dataFilePath ?? ""
                    }
                    graphs.append(graph)
                }
            }

            // Analyses
            var analyses: [Analysis] = []
            if let analysesArr = expDict["analyses"] as? [[String: Any]] {
                for ad in analysesArr {
                    guard let aid = (ad["id"] as? String).flatMap({ UUID(uuidString: $0) }),
                          let dtid = (ad["dataTableID"] as? String).flatMap({ UUID(uuidString: $0) }) else { continue }
                    let analysis = Analysis(id: aid, label: ad["label"] as? String ?? "", dataTableID: dtid, analysisType: ad["analysisType"] as? String ?? "")
                    analysis.notes = ad["notes"] as? String ?? ""
                    analyses.append(analysis)
                }
            }

            let experiment = Experiment(id: expID, label: label, dataTables: tables, graphs: graphs, analyses: analyses, info: info)
            restored.append(experiment)
        }

        experiments = restored
    }

    /// Convert legacy dataTables format into experiment format.
    private func restoreLegacyProject(_ tablesArray: [[String: Any]], project: [String: Any]) {
        let experiment = Experiment(label: "Experiment 1")
        var tables: [DataTable] = []
        var graphs: [Graph] = []
        var analyses: [Analysis] = []

        for tableDict in tablesArray {
            guard let idStr = tableDict["id"] as? String,
                  let tableID = UUID(uuidString: idStr),
                  let typeStr = tableDict["tableType"] as? String,
                  let tableType = TableType(rawValue: typeStr) else { continue }

            let table = DataTable(id: tableID, label: tableDict["label"] as? String ?? "Untitled", tableType: tableType, dataFilePath: tableDict["dataFilePath"] as? String, originalFileName: tableDict["originalFileName"] as? String)

            // Skip tables whose data files no longer exist
            if let path = table.dataFilePath, !path.isEmpty,
               !FileManager.default.fileExists(atPath: path) {
                continue
            }

            tables.append(table)

            // Convert sheets to graphs/analyses
            if let sheetsArray = tableDict["sheets"] as? [[String: Any]] {
                for sheetDict in sheetsArray {
                    guard let sid = (sheetDict["id"] as? String).flatMap({ UUID(uuidString: $0) }),
                          let kindStr = sheetDict["kind"] as? String else { continue }

                    if kindStr == "graph" {
                        guard let ct = (sheetDict["chartType"] as? String).flatMap({ ChartType(rawValue: $0) }) else { continue }
                        let graph = Graph(id: sid, label: sheetDict["label"] as? String ?? "", dataTableID: tableID, chartType: ct)
                        if let configDict = sheetDict["chartConfig"] as? [String: Any] {
                            graph.chartConfig.loadFromDict(configDict)
                        }
                        if let path = table.dataFilePath {
                            graph.chartConfig.excelPath = path
                        }
                        if let fgDict = sheetDict["formatSettings"] as? [String: Any],
                           let fgData = try? JSONSerialization.data(withJSONObject: fgDict),
                           let fg = try? JSONDecoder().decode(FormatGraphSettings.self, from: fgData) {
                            graph.formatSettings = fg
                        }
                        if let faDict = sheetDict["formatAxesSettings"] as? [String: Any],
                           let faData = try? JSONSerialization.data(withJSONObject: faDict),
                           let fa = try? JSONDecoder().decode(FormatAxesSettings.self, from: faData) {
                            graph.formatAxesSettings = fa
                        }
                        graphs.append(graph)
                    } else if kindStr == "results" {
                        let analysis = Analysis(id: sid, label: sheetDict["label"] as? String ?? "", dataTableID: tableID)
                        analysis.notes = sheetDict["notes"] as? String ?? ""
                        analyses.append(analysis)
                    }
                }
            }
        }

        experiment.dataTables = tables
        experiment.graphs = graphs
        experiment.analyses = analyses
        experiments = [experiment]

        activeExperimentID = experiment.id
        activeItemID = tables.first?.id
        activeItemKind = .dataTable
    }

    // MARK: - Project Persistence

    func saveProjectState() -> ProjectState {
        ProjectState(
            experiments: experiments.map { exp in
                ProjectState.ExperimentState(
                    id: exp.id.uuidString,
                    label: exp.label,
                    dataTables: exp.dataTables.map { t in
                        ProjectState.DataTableState(
                            id: t.id.uuidString,
                            label: t.label,
                            tableType: t.tableType.rawValue,
                            dataFilePath: t.dataFilePath,
                            originalFileName: t.originalFileName
                        )
                    },
                    graphs: exp.graphs.map { g in
                        ProjectState.GraphState(
                            id: g.id.uuidString,
                            label: g.label,
                            dataTableID: g.dataTableID.uuidString,
                            chartType: g.chartType.rawValue
                        )
                    },
                    analyses: exp.analyses.map { a in
                        ProjectState.AnalysisState(
                            id: a.id.uuidString,
                            label: a.label,
                            dataTableID: a.dataTableID.uuidString,
                            analysisType: a.analysisType,
                            notes: a.notes.isEmpty ? nil : a.notes
                        )
                    }
                )
            },
            activeExperimentID: activeExperimentID?.uuidString,
            activeItemID: activeItemID?.uuidString,
            activeItemKind: activeItemKind?.rawValue
        )
    }

    func projectStateJSON() -> String {
        let state = saveProjectState()
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        guard let data = try? encoder.encode(state) else { return "{}" }
        return String(data: data, encoding: .utf8) ?? "{}"
    }

    func saveProject() {
        saveProjectState().writeToDisk()
    }

    func loadProjectIfExists() {
        guard let state = ProjectState.readFromDisk() else { return }
        var restoredExperiments: [Experiment] = []
        for es in state.experiments {
            guard let expID = UUID(uuidString: es.id) else { continue }
            var tables: [DataTable] = []
            for ts in es.dataTables {
                guard let tid = UUID(uuidString: ts.id),
                      let tt = TableType(rawValue: ts.tableType) else { continue }
                if let path = ts.dataFilePath, !path.isEmpty,
                   !FileManager.default.fileExists(atPath: path) { continue }
                tables.append(DataTable(id: tid, label: ts.label, tableType: tt, dataFilePath: ts.dataFilePath, originalFileName: ts.originalFileName))
            }
            var graphs: [Graph] = []
            for gs in es.graphs {
                guard let gid = UUID(uuidString: gs.id),
                      let dtid = UUID(uuidString: gs.dataTableID),
                      let ct = ChartType(rawValue: gs.chartType) else { continue }
                graphs.append(Graph(id: gid, label: gs.label, dataTableID: dtid, chartType: ct))
            }
            var analyses: [Analysis] = []
            for ans in es.analyses {
                guard let aid = UUID(uuidString: ans.id),
                      let dtid = UUID(uuidString: ans.dataTableID) else { continue }
                let a = Analysis(id: aid, label: ans.label, dataTableID: dtid, analysisType: ans.analysisType)
                if let notes = ans.notes { a.notes = notes }
                analyses.append(a)
            }
            guard !tables.isEmpty else { continue }
            restoredExperiments.append(Experiment(id: expID, label: es.label, dataTables: tables, graphs: graphs, analyses: analyses))
        }
        guard !restoredExperiments.isEmpty else { return }
        experiments = restoredExperiments
        activeExperimentID = state.activeExperimentID.flatMap { UUID(uuidString: $0) }
        activeItemID = state.activeItemID.flatMap { UUID(uuidString: $0) }
        activeItemKind = state.activeItemKind.flatMap { ItemKind(rawValue: $0) }
    }

    // MARK: - Save as .refract File

    @MainActor
    func saveProjectFile() async {
        if let existingPath = projectFilePath {
            await saveToPath(existingPath)
        } else {
            await saveProjectFileAs()
        }
    }

    @MainActor
    func saveProjectFileAs() async {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [
            .init(filenameExtension: "refract") ?? .data
        ]
        panel.nameFieldStringValue = projectFilePath?.lastPathComponent ?? untitledName
        panel.title = "Save Project"
        panel.prompt = "Save"

        guard panel.runModal() == .OK, let url = panel.url else { return }
        await saveToPath(url)
    }

    @MainActor
    private func saveToPath(_ url: URL) async {
        DebugLog.shared.logAppEvent("saveToPath(\(url.lastPathComponent))", detail: "path: \(url.path)")
        let projectDict = buildFullProjectDict()

        do {
            let _ = try await APIClient.shared.saveProject(
                outputPath: url.path,
                projectState: projectDict
            )
            if let n = currentUntitledNumber {
                Self.activeUntitledNumbers.remove(n)
            }
            Self.openProjectPaths.insert(url.standardizedFileURL.path)
            projectFilePath = url
            hasUnsavedChanges = false
            RecentFiles.shared.add(url)
        } catch {
            self.error = "Save failed: \(error.localizedDescription)"
        }
    }

    func markDirty() {
        hasUnsavedChanges = true
    }

    private func buildFullProjectDict() -> [String: Any] {
        let exps: [[String: Any]] = experiments.map { exp in
            let tables: [[String: Any]] = exp.dataTables.map { t in
                var d: [String: Any] = [
                    "id": t.id.uuidString,
                    "label": t.label,
                    "tableType": t.tableType.rawValue,
                ]
                if let path = t.dataFilePath { d["dataFilePath"] = path }
                if let name = t.originalFileName { d["originalFileName"] = name }
                return d
            }
            let graphs: [[String: Any]] = exp.graphs.map { g in
                var d: [String: Any] = [
                    "id": g.id.uuidString,
                    "label": g.label,
                    "dataTableID": g.dataTableID.uuidString,
                    "chartType": g.chartType.rawValue,
                    "chartConfig": g.chartConfig.toDict(),
                ]
                if let fgData = try? JSONEncoder().encode(g.formatSettings),
                   let fgDict = try? JSONSerialization.jsonObject(with: fgData) as? [String: Any] {
                    d["formatSettings"] = fgDict
                }
                if let faData = try? JSONEncoder().encode(g.formatAxesSettings),
                   let faDict = try? JSONSerialization.jsonObject(with: faData) as? [String: Any] {
                    d["formatAxesSettings"] = faDict
                }
                d["renderStyle"] = g.renderStyle.rawValue
                return d
            }
            let analyses: [[String: Any]] = exp.analyses.map { a in
                var d: [String: Any] = [
                    "id": a.id.uuidString,
                    "label": a.label,
                    "dataTableID": a.dataTableID.uuidString,
                    "analysisType": a.analysisType,
                ]
                if !a.notes.isEmpty { d["notes"] = a.notes }
                return d
            }
            return [
                "id": exp.id.uuidString,
                "label": exp.label,
                "info": exp.info,
                "dataTables": tables,
                "graphs": graphs,
                "analyses": analyses,
            ]
        }

        return [
            "experiments": exps,
            "activeExperimentID": activeExperimentID?.uuidString ?? "",
            "activeItemID": activeItemID?.uuidString ?? "",
            "activeItemKind": activeItemKind?.rawValue ?? "",
        ]
    }

    // MARK: - Utilities

    func dismissError() {
        error = nil
    }

    @MainActor
    func retryLastAction() async {
        error = nil
        await generatePlot()
    }
}

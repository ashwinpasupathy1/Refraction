// NewDataTableDialog.swift — Prism-style dialog for creating a new data table.
// Left sidebar: table types. Right panel: name, upload, sheet picker, validation.
// Create button is disabled until data is uploaded and validated.

import SwiftUI
import UniformTypeIdentifiers

struct NewDataTableDialog: View {

    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    @State private var selectedType: TableType = .column
    @State private var name: String = ""

    // Upload state
    @State private var uploadedFilePath: String?
    @State private var uploadedFileName: String?
    @State private var isUploading = false

    // Sheet picker (Excel only)
    @State private var sheetNames: [String] = []
    @State private var selectedSheet: String?
    @State private var isCSV = false

    // Validation state
    @State private var isValidating = false
    @State private var validationPassed = false
    @State private var validationErrors: [String] = []
    @State private var validationWarnings: [String] = []

    private var defaultName: String {
        let count = appState.activeExperiment?.dataTables.count ?? 0
        return "\(selectedType.label) \(count + 1)"
    }

    private var effectiveName: String {
        let trimmed = name.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? defaultName : trimmed
    }

    private var canCreate: Bool {
        validationPassed && !isUploading && !isValidating
    }

    var body: some View {
        VStack(spacing: 0) {
            // Title
            Text("New Data Table")
                .font(.headline)
                .padding(.top, 16)
                .padding(.bottom, 8)

            Divider()

            // Main content: type sidebar + detail
            HStack(spacing: 0) {
                typeSidebar
                    .frame(width: 180)

                Divider()

                detailPanel
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .frame(height: 440)

            Divider()

            // Bottom buttons
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)

                Button("Create") { create() }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
                    .disabled(!canCreate)
            }
            .padding(16)
        }
        .frame(width: 640)
    }

    // MARK: - Type Sidebar

    private var typeSidebar: some View {
        List(TableType.allCases, selection: $selectedType) { type in
            Label(type.label, systemImage: type.sfSymbol)
                .tag(type)
        }
        .listStyle(.sidebar)
        .onChange(of: selectedType) { _, _ in
            // Reset validation when type changes (data may no longer match)
            if uploadedFilePath != nil {
                Task { await runValidation() }
            }
        }
    }

    // MARK: - Detail Panel

    private var detailPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                // Type title + description
                Text("\(selectedType.label) Tables")
                    .font(.title2)
                    .fontWeight(.semibold)
                    .foregroundStyle(.blue)

                Text(typeDescription(selectedType))
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                // Data layout preview
                dataLayoutPreview(selectedType)
                    .padding(.vertical, 2)

                Divider()

                // MARK: - Upload section
                VStack(alignment: .leading, spacing: 8) {
                    Text("Data File")
                        .font(.subheadline)
                        .fontWeight(.semibold)

                    HStack {
                        if let fileName = uploadedFileName {
                            Image(systemName: "doc.fill")
                                .foregroundStyle(.green)
                            Text(fileName)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        } else {
                            Text("No file selected")
                                .foregroundStyle(.secondary)
                        }
                        Spacer()

                        Button {
                            openFilePicker()
                        } label: {
                            Label(uploadedFilePath == nil ? "Upload..." : "Change...",
                                  systemImage: "arrow.up.doc")
                        }
                        .disabled(isUploading)
                    }

                    if isUploading {
                        HStack(spacing: 6) {
                            ProgressView().controlSize(.small)
                            Text("Uploading...")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                // MARK: - Sheet picker (Excel only)
                if !isCSV && sheetNames.count > 1 {
                    LabeledContent("Sheet") {
                        Picker("", selection: Binding(
                            get: { selectedSheet ?? sheetNames.first ?? "" },
                            set: { newSheet in
                                selectedSheet = newSheet
                                Task { await runValidation() }
                            }
                        )) {
                            ForEach(sheetNames, id: \.self) { sheet in
                                Text(sheet).tag(sheet)
                            }
                        }
                        .labelsHidden()
                        .frame(maxWidth: 200)
                    }
                }

                // MARK: - Validation status
                if uploadedFilePath != nil {
                    Divider()
                    validationStatusView
                }

                Divider()

                // Name field
                VStack(alignment: .leading, spacing: 4) {
                    Text("Name")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    TextField(defaultName, text: $name)
                        .textFieldStyle(.roundedBorder)
                        .onSubmit { if canCreate { create() } }
                }
            }
            .padding(20)
        }
    }

    // MARK: - Validation Status

    @ViewBuilder
    private var validationStatusView: some View {
        if isValidating {
            HStack(spacing: 6) {
                ProgressView().controlSize(.small)
                Text("Validating...")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        } else if validationPassed {
            HStack(spacing: 4) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                Text("Data format is valid")
                    .font(.caption)
                    .foregroundStyle(.green)
            }
            if !validationWarnings.isEmpty {
                ForEach(validationWarnings, id: \.self) { warning in
                    HStack(spacing: 4) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                            .font(.caption2)
                        Text(warning)
                            .font(.caption2)
                            .foregroundStyle(.orange)
                    }
                }
            }
        } else if !validationErrors.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 4) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.red)
                    Text("Format Error")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.red)
                }
                ForEach(validationErrors, id: \.self) { err in
                    Text("• \(err)")
                        .font(.caption2)
                        .foregroundStyle(.red)
                }
            }
        }
    }

    // MARK: - Data Layout Preview

    @ViewBuilder
    private func dataLayoutPreview(_ type: TableType) -> some View {
        let layout = layoutInfo(type)
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 0) {
                ForEach(Array(layout.headers.enumerated()), id: \.offset) { _, header in
                    Text(header)
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                        .frame(width: headerWidth(layout.headers.count), alignment: .center)
                        .padding(.vertical, 4)
                        .background(Color.blue.opacity(0.1))
                }
            }

            Divider()

            ForEach(Array(layout.rows.enumerated()), id: \.offset) { _, row in
                HStack(spacing: 0) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                        Text(cell)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.secondary)
                            .frame(width: headerWidth(layout.headers.count), alignment: .center)
                            .padding(.vertical, 2)
                    }
                }
            }
        }
        .overlay(
            RoundedRectangle(cornerRadius: 4)
                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 4))
    }

    private func headerWidth(_ count: Int) -> CGFloat {
        max(60, 380 / CGFloat(count))
    }

    // MARK: - Actions

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType(filenameExtension: "xlsx")!,
            UTType(filenameExtension: "xls")!,
            UTType(filenameExtension: "csv")!,
        ]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.message = "Select a data file for this table"

        guard panel.runModal() == .OK, let url = panel.url else { return }

        isCSV = url.pathExtension.lowercased() == "csv"
        uploadedFileName = url.lastPathComponent

        Task { await uploadAndValidate(url: url) }
    }

    private func uploadAndValidate(url: URL) async {
        isUploading = true
        validationPassed = false
        validationErrors = []
        validationWarnings = []

        do {
            let serverPath = try await APIClient.shared.upload(fileURL: url)
            uploadedFilePath = serverPath

            // For Excel files, get sheet names
            if !isCSV {
                let sheets = try await APIClient.shared.listSheets(excelPath: serverPath)
                await MainActor.run {
                    sheetNames = sheets
                    selectedSheet = sheets.first
                }
            } else {
                await MainActor.run {
                    sheetNames = []
                    selectedSheet = nil
                }
            }

            isUploading = false
            await runValidation()
        } catch {
            await MainActor.run {
                isUploading = false
                validationErrors = ["Upload failed: \(error.localizedDescription)"]
            }
        }
    }

    private func runValidation() async {
        guard let path = uploadedFilePath else { return }
        isValidating = true
        validationPassed = false
        validationErrors = []
        validationWarnings = []

        do {
            let result: ValidationResponse
            if isCSV || selectedSheet == nil {
                result = try await APIClient.shared.validateTable(
                    excelPath: path,
                    tableType: selectedType.rawValue
                )
            } else {
                result = try await APIClient.shared.validateTable(
                    excelPath: path,
                    tableType: selectedType.rawValue,
                    sheetName: selectedSheet
                )
            }

            await MainActor.run {
                isValidating = false
                if let valid = result.valid {
                    validationPassed = valid
                    validationErrors = result.errors ?? []
                    validationWarnings = result.warnings ?? []
                } else {
                    validationErrors = [result.error ?? "Validation failed"]
                }
            }
        } catch {
            await MainActor.run {
                isValidating = false
                validationErrors = ["Validation failed: \(error.localizedDescription)"]
            }
        }
    }

    private func create() {
        guard let experiment = appState.activeExperiment else { return }
        let table = experiment.addDataTable(type: selectedType, label: effectiveName)
        table.originalFileName = uploadedFileName

        // Populate in-memory data from uploaded file
        if let serverPath = uploadedFilePath {
            Task {
                do {
                    let preview = try await APIClient.shared.dataPreview(excelPath: serverPath)
                    if let cols = preview.columns, let rawRows = preview.rows {
                        await MainActor.run {
                            table.columns = cols
                            table.rows = rawRows.map { row in
                                row.map { cell -> CellValue in
                                    switch cell {
                                    case .number(let d): return .number(d)
                                    case .string(let s):
                                        if let d = Double(s) { return .number(d) }
                                        return s.isEmpty ? .empty : .text(s)
                                    case .null: return .empty
                                    }
                                }
                            }
                            appState.markDirty()
                        }
                    }
                } catch {
                    DebugLog.shared.logAppEvent("Failed to load data into table: \(error.localizedDescription)")
                }
            }
        }

        appState.selectItem(table.id, kind: .dataTable)
        appState.markDirty()
        dismiss()
    }

    // MARK: - Type Descriptions

    private func typeDescription(_ type: TableType) -> String {
        switch type {
        case .xy:
            return "Each point is defined by an X and Y coordinate. Use for scatter plots, line graphs, dose-response curves, and time series. Repeat a series name across multiple columns for replicates — means and error bars (SEM/SD/CI95) are computed automatically."
        case .column:
            return "Each column is a group with numeric values in rows. Use for bar charts, box plots, violin plots, and comparing group means. Each row is one replicate — add more rows for more replicates per group. Means and error bars are computed automatically."
        case .grouped:
            return "Data organized by two factors: rows are categories, columns are subgroups. Use for grouped bar charts and stacked bars. Repeat the same category name across multiple rows for replicates. Means and error bars are computed automatically."
        case .contingency:
            return "A matrix of counts for categorical data. Rows are groups, columns are outcomes. Use for chi-square tests and contingency analysis."
        case .survival:
            return "Time-to-event data with censoring. Each group has paired Time and Event (0/1) columns. Use for Kaplan-Meier survival curves. Each row is one subject — add more rows for more subjects per group."
        case .parts:
            return "Categories with values representing parts of a whole. Use for waterfall charts and pyramid plots."
        case .multipleVariables:
            return "Multiple measured variables per subject. Rows are observations, columns are variables. Use for heatmaps and multivariate scatter. Each row is one replicate — add more rows for more observations."
        case .nested:
            return "Hierarchical data with subgroups nested within groups. Use for subcolumn scatter and nested comparisons. Repeat the same group/subgroup across rows for replicates."
        case .twoWay:
            return "Each observation has two factors and a response value. Columns are Factor A, Factor B, and Value. Use for two-way ANOVA. Repeat factor combinations across rows for replicates — means are computed automatically."
        case .comparison:
            return "Paired measurements for comparing two methods or time points. Use for before-after plots and Bland-Altman analysis. Each row is one paired replicate — add more rows for more pairs."
        case .meta:
            return "Summary statistics from multiple studies. Columns are Study, Effect Size, Lower CI, Upper CI. Use for forest plots."
        }
    }

    // MARK: - Layout Info

    private struct LayoutInfo {
        let headers: [String]
        let rows: [[String]]
    }

    private func layoutInfo(_ type: TableType) -> LayoutInfo {
        switch type {
        case .xy:
            // 3 replicates of Series Y — repeated column name signals replicates
            return LayoutInfo(
                headers: ["X", "Y", "Y", "Y"],
                rows: [
                    ["0", "2.1", "3.4", "1.8"],
                    ["1", "4.5", "5.2", "3.9"],
                    ["2", "7.8", "8.1", "6.5"],
                ]
            )
        case .column:
            // Each row is one replicate per group (3 replicates shown)
            return LayoutInfo(
                headers: ["Control", "Drug A", "Drug B"],
                rows: [
                    ["5.2", "8.1", "12.3"],
                    ["4.8", "7.9", "11.8"],
                    ["5.5", "8.5", "13.1"],
                ]
            )
        case .grouped:
            // 3 replicate rows per category (same category name repeated)
            return LayoutInfo(
                headers: ["Category", "Male", "Female"],
                rows: [
                    ["Young", "45", "52"],
                    ["Young", "47", "49"],
                    ["Young", "43", "55"],
                ]
            )
        case .contingency:
            return LayoutInfo(
                headers: ["", "Positive", "Negative"],
                rows: [["Treatment", "45", "15"], ["Placebo", "20", "40"]]
            )
        case .survival:
            // 3 subjects per group
            return LayoutInfo(
                headers: ["Grp A Time", "Grp A Event", "Grp B Time", "Grp B Event"],
                rows: [
                    ["5", "1", "3", "1"],
                    ["12", "0", "8", "1"],
                    ["18", "1", "15", "0"],
                ]
            )
        case .parts:
            return LayoutInfo(
                headers: ["Category", "Value"],
                rows: [["Revenue", "500"], ["Cost", "-200"], ["Tax", "-75"]]
            )
        case .multipleVariables:
            // 3 replicates (rows) across 3 variables
            return LayoutInfo(
                headers: ["Var 1", "Var 2", "Var 3"],
                rows: [
                    ["1.2", "3.4", "5.6"],
                    ["2.3", "4.5", "6.7"],
                    ["3.4", "5.6", "7.8"],
                ]
            )
        case .nested:
            // 3 observations nested within groups
            return LayoutInfo(
                headers: ["Group", "Subgroup", "Value"],
                rows: [
                    ["A", "A1", "5.2"],
                    ["A", "A1", "4.8"],
                    ["A", "A1", "5.5"],
                ]
            )
        case .twoWay:
            // 3 replicate observations per factor combination
            return LayoutInfo(
                headers: ["Factor A", "Factor B", "Value"],
                rows: [
                    ["Low", "Male", "23.5"],
                    ["Low", "Male", "25.1"],
                    ["Low", "Male", "22.8"],
                ]
            )
        case .comparison:
            // 3 paired replicates
            return LayoutInfo(
                headers: ["Method A", "Method B"],
                rows: [
                    ["5.2", "5.8"],
                    ["4.9", "5.3"],
                    ["6.1", "6.5"],
                ]
            )
        case .meta:
            return LayoutInfo(
                headers: ["Study", "Effect", "Lower CI", "Upper CI"],
                rows: [["Smith 2020", "0.85", "0.62", "1.15"], ["Jones 2021", "1.23", "0.98", "1.54"]]
            )
        }
    }
}

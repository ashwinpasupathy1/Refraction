// DataTableView.swift — Editable spreadsheet view backed by in-memory DataTable.
// Shows a file picker if no data is loaded.

import SwiftUI
import UniformTypeIdentifiers

struct DataTableView: View {

    @Environment(AppState.self) private var appState

    var body: some View {
        if let table = appState.activeDataTable, table.hasData {
            spreadsheetView(table: table)
        } else {
            filePickerPrompt
        }
    }

    // MARK: - File Picker

    private var filePickerPrompt: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(.quaternary)
            Text("Import Data")
                .font(.title2)
                .foregroundStyle(.secondary)
            Text("Choose an Excel or CSV file to load into this table.")
                .font(.body)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)

            Button("Open File...") {
                openFilePicker()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(40)
    }

    // MARK: - Spreadsheet View

    private func spreadsheetView(table: DataTable) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            // Toolbar
            HStack {
                Image(systemName: "tablecells")
                Text(table.originalFileName ?? table.label)
                    .font(.headline)
                Text("(\(table.tableType.label))")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                Text("\(table.rowCount) rows \u{00d7} \(table.columnCount) cols")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()

                Button {
                    table.addColumn()
                    appState.markDirty()
                } label: {
                    Label("Add Column", systemImage: "plus.rectangle")
                }
                .controlSize(.small)
                .buttonStyle(.bordered)

                Button {
                    table.addRow()
                    appState.markDirty()
                } label: {
                    Label("Add Row", systemImage: "plus.rectangle.portrait")
                }
                .controlSize(.small)
                .buttonStyle(.bordered)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)

            Divider()

            // Spreadsheet grid
            ScrollView([.horizontal, .vertical]) {
                LazyVStack(alignment: .leading, spacing: 0, pinnedViews: [.sectionHeaders]) {
                    Section {
                        ForEach(0..<table.rowCount, id: \.self) { rowIdx in
                            HStack(spacing: 0) {
                                // Row number
                                Text("\(rowIdx + 1)")
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                    .frame(width: 36, alignment: .trailing)
                                    .padding(.horizontal, 4)
                                    .padding(.vertical, 2)
                                    .background(Color.gray.opacity(0.08))

                                ForEach(0..<table.columnCount, id: \.self) { colIdx in
                                    CellEditor(table: table, row: rowIdx, col: colIdx)
                                }
                            }
                            .background(rowIdx % 2 == 0 ? Color.clear : Color.gray.opacity(0.03))

                            Divider()
                        }
                    } header: {
                        VStack(spacing: 0) {
                            HStack(spacing: 0) {
                                Text("#")
                                    .fontWeight(.semibold)
                                    .font(.caption)
                                    .frame(width: 36, alignment: .trailing)
                                    .padding(.horizontal, 4)
                                    .padding(.vertical, 4)

                                ForEach(0..<table.columnCount, id: \.self) { colIdx in
                                    ColumnHeader(table: table, col: colIdx)
                                }
                            }
                            .background(.bar)

                            Divider()
                        }
                    }
                }
            }
        }
    }

    // MARK: - Actions

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType(filenameExtension: "xlsx")!,
            UTType(filenameExtension: "xls")!,
            UTType(filenameExtension: "csv")!,
        ]
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false

        if panel.runModal() == .OK, let url = panel.url {
            let table = appState.activeDataTable
            Task {
                await appState.uploadFile(url: url, for: table)
            }
        }
    }
}

// MARK: - Cell Editor

private struct CellEditor: View {
    let table: DataTable
    let row: Int
    let col: Int

    @Environment(AppState.self) private var appState
    @State private var editText: String = ""
    @State private var isEditing = false
    @FocusState private var isFocused: Bool

    var body: some View {
        if isEditing {
            TextField("", text: $editText, onCommit: commit)
                .textFieldStyle(.plain)
                .font(.system(.body, design: .monospaced))
                .focused($isFocused)
                .frame(width: 120, alignment: .leading)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.accentColor.opacity(0.08))
                .onAppear { isFocused = true }
                .onExitCommand { cancelEdit() }
        } else {
            Text(table.cell(row: row, col: col).displayString)
                .font(.system(.body, design: .monospaced))
                .lineLimit(1)
                .frame(width: 120, alignment: .leading)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .contentShape(Rectangle())
                .onTapGesture(count: 2) { startEdit() }
        }
    }

    private func startEdit() {
        editText = table.cell(row: row, col: col).displayString
        isEditing = true
    }

    private func commit() {
        let trimmed = editText.trimmingCharacters(in: .whitespaces)
        let newValue: CellValue
        if trimmed.isEmpty {
            newValue = .empty
        } else if let d = Double(trimmed) {
            newValue = .number(d)
        } else {
            newValue = .text(trimmed)
        }
        let oldValue = table.cell(row: row, col: col)
        guard oldValue != newValue else {
            isEditing = false
            return
        }
        table.setCell(row: row, col: col, value: newValue)
        appState.registerCellEdit(table: table, row: row, col: col, oldValue: oldValue, newValue: newValue)
        appState.markDirty()
        isEditing = false
        DebugLog.shared.logVerbose("cell edit [\(row),\(col)] = \(trimmed)")
    }

    private func cancelEdit() {
        isEditing = false
    }
}

// MARK: - Column Header

private struct ColumnHeader: View {
    let table: DataTable
    let col: Int

    @Environment(AppState.self) private var appState
    @State private var editText: String = ""
    @State private var isEditing = false
    @FocusState private var isFocused: Bool

    var body: some View {
        if isEditing {
            TextField("", text: $editText, onCommit: commit)
                .textFieldStyle(.plain)
                .fontWeight(.semibold)
                .focused($isFocused)
                .frame(width: 120, alignment: .leading)
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .onAppear { isFocused = true }
        } else {
            Text(col < table.columns.count ? table.columns[col] : "")
                .fontWeight(.semibold)
                .lineLimit(1)
                .frame(width: 120, alignment: .leading)
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .contentShape(Rectangle())
                .onTapGesture(count: 2) {
                    editText = col < table.columns.count ? table.columns[col] : ""
                    isEditing = true
                }
        }
    }

    private func commit() {
        if col < table.columns.count {
            table.columns[col] = editText
            appState.markDirty()
            DebugLog.shared.logVerbose("rename column[\(col)] = \(editText)")
        }
        isEditing = false
    }
}

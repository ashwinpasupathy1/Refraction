// DataTable.swift — A data table within an experiment.
// Owns its data in-memory as a 2D matrix of CellValues.
// Graphs and analyses reference data tables by ID.

import Foundation

// MARK: - Cell Value

/// A single cell in a data table — either a number, text, or empty.
enum CellValue: Codable, Equatable, Hashable {
    case number(Double)
    case text(String)
    case empty

    /// Display string for the cell.
    var displayString: String {
        switch self {
        case .number(let v):
            // Avoid trailing .0 for integers
            return v == v.rounded() && abs(v) < 1e15 ? String(format: "%.0f", v) : String(v)
        case .text(let s): return s
        case .empty: return ""
        }
    }

    /// Numeric value if available (for analysis).
    var doubleValue: Double? {
        switch self {
        case .number(let v): return v
        case .text(let s): return Double(s)
        case .empty: return nil
        }
    }

    // MARK: - Codable

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .empty
        } else if let v = try? container.decode(Double.self) {
            self = .number(v)
        } else if let s = try? container.decode(String.self) {
            if let v = Double(s) {
                self = .number(v)
            } else if s.isEmpty {
                self = .empty
            } else {
                self = .text(s)
            }
        } else {
            self = .empty
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .number(let v): try container.encode(v)
        case .text(let s): try container.encode(s)
        case .empty: try container.encodeNil()
        }
    }
}

// MARK: - DataTable

@Observable
final class DataTable: Identifiable {
    let id: UUID
    var label: String
    var tableType: TableType
    var columns: [String]
    var rows: [[CellValue]]
    var originalFileName: String?

    /// Whether data has been loaded into this table.
    var hasData: Bool {
        !columns.isEmpty && !rows.isEmpty
    }

    /// Number of data rows.
    var rowCount: Int { rows.count }

    /// Number of columns.
    var columnCount: Int { columns.count }

    /// Valid chart types based on table type.
    var availableChartTypes: [ChartType] {
        tableType.validChartTypes
    }

    var sfSymbol: String { "tablecells" }

    init(
        id: UUID = UUID(),
        label: String,
        tableType: TableType,
        columns: [String] = [],
        rows: [[CellValue]] = [],
        originalFileName: String? = nil
    ) {
        self.id = id
        self.label = label
        self.tableType = tableType
        self.columns = columns
        self.rows = rows
        self.originalFileName = originalFileName
    }

    // MARK: - Cell Access

    /// Get a cell value safely.
    func cell(row: Int, col: Int) -> CellValue {
        guard row >= 0, row < rows.count, col >= 0, col < rows[row].count else { return .empty }
        return rows[row][col]
    }

    /// Set a cell value, expanding the grid if needed.
    func setCell(row: Int, col: Int, value: CellValue) {
        // Expand rows if needed
        while rows.count <= row {
            rows.append(Array(repeating: .empty, count: columns.count))
        }
        // Expand columns in this row if needed
        while rows[row].count <= col {
            rows[row].append(.empty)
        }
        rows[row][col] = value
    }

    // MARK: - Row/Column Operations

    func addRow() {
        rows.append(Array(repeating: .empty, count: max(columns.count, 1)))
    }

    func addColumn(name: String = "") {
        let colName = name.isEmpty ? "Col \(columns.count + 1)" : name
        columns.append(colName)
        for i in 0..<rows.count {
            rows[i].append(.empty)
        }
    }

    func removeRow(at index: Int) {
        guard index >= 0, index < rows.count else { return }
        rows.remove(at: index)
    }

    func removeColumn(at index: Int) {
        guard index >= 0, index < columns.count else { return }
        columns.remove(at: index)
        for i in 0..<rows.count {
            if index < rows[i].count {
                rows[i].remove(at: index)
            }
        }
    }

    // MARK: - JSON Persistence (for .refract bundle)

    /// JSON structure for bundle storage.
    struct DataJSON: Codable {
        let columns: [String]
        let rows: [[CellValue]]
    }

    func toJSON() throws -> Data {
        let dataJSON = DataJSON(columns: columns, rows: rows)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(dataJSON)
    }

    static func fromJSON(_ data: Data, id: UUID, label: String, tableType: TableType, originalFileName: String? = nil) throws -> DataTable {
        let decoded = try JSONDecoder().decode(DataJSON.self, from: data)
        return DataTable(
            id: id,
            label: label,
            tableType: tableType,
            columns: decoded.columns,
            rows: decoded.rows,
            originalFileName: originalFileName
        )
    }

    // MARK: - Analyze Payload

    /// Build the data payload for the /analyze endpoint.
    /// Returns {"columns": [...], "rows": [[...], ...]} with raw values.
    func toAnalyzePayload() -> [String: Any] {
        let rawRows: [[Any?]] = rows.map { row in
            row.map { cell -> Any? in
                switch cell {
                case .number(let v): return v
                case .text(let s): return s
                case .empty: return nil
                }
            }
        }
        return ["columns": columns, "rows": rawRows]
    }

    // MARK: - Import from parsed server response

    /// Populate from a server response dict (e.g., from /data-preview or /import-data).
    func loadFromServerResponse(columns cols: [String], rows rawRows: [[Any?]]) {
        columns = cols
        rows = rawRows.map { row in
            row.map { val -> CellValue in
                if val == nil || val is NSNull {
                    return .empty
                } else if let n = val as? Double {
                    return .number(n)
                } else if let n = val as? Int {
                    return .number(Double(n))
                } else if let s = val as? String {
                    if let d = Double(s) { return .number(d) }
                    return s.isEmpty ? .empty : .text(s)
                } else {
                    return .text(String(describing: val!))
                }
            }
        }
    }
}

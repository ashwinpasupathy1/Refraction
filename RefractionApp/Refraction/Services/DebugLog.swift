// DebugLog.swift — Centralized debug logger for API calls, app events, and engine traces.
// Captures timestamped entries for display in the debug console.

import Foundation

@Observable
final class DebugLog {

    static let shared = DebugLog()

    struct Entry: Identifiable {
        let id = UUID()
        let timestamp: Date
        let kind: Kind
        let method: String       // e.g. "POST /render", "APP", "ENGINE"
        let summary: String      // short description
        let detail: String       // full request/response JSON or trace
        let durationMs: Int?     // round-trip time
        let isError: Bool

        enum Kind: String {
            case request  = "REQ"
            case response = "RES"
            case error    = "ERR"
            case app      = "APP"
            case engine   = "ENG"
            case ui       = "UI"
            case verbose  = "VRB"
        }

        /// Whether this is a verbose (high-frequency) entry that can be filtered out.
        var isVerbose: Bool { kind == .verbose }

        var timestampString: String {
            Self.formatter.string(from: timestamp)
        }

        private static let formatter: DateFormatter = {
            let f = DateFormatter()
            f.dateFormat = "HH:mm:ss.SSS"
            return f
        }()
    }

    private(set) var entries: [Entry] = []

    /// Maximum entries to keep (ring buffer).
    private let maxEntries = 500

    func logRequest(method: String, path: String, body: String) {
        append(Entry(
            timestamp: Date(),
            kind: .request,
            method: "\(method) \(path)",
            summary: "→ \(method) \(path)",
            detail: body,
            durationMs: nil,
            isError: false
        ))
    }

    func logResponse(method: String, path: String, statusCode: Int, body: String, durationMs: Int) {
        let isErr = statusCode >= 400
        append(Entry(
            timestamp: Date(),
            kind: isErr ? .error : .response,
            method: "\(method) \(path)",
            summary: "← \(statusCode) \(path) (\(durationMs)ms)",
            detail: body,
            durationMs: durationMs,
            isError: isErr
        ))
    }

    func logError(method: String, path: String, error: String) {
        append(Entry(
            timestamp: Date(),
            kind: .error,
            method: "\(method) \(path)",
            summary: "✖ \(path): \(error)",
            detail: error,
            durationMs: nil,
            isError: true
        ))
    }

    func logAppEvent(_ message: String, detail: String = "") {
        append(Entry(
            timestamp: Date(),
            kind: .app,
            method: "APP",
            summary: "● \(message)",
            detail: detail.isEmpty ? message : detail,
            durationMs: nil,
            isError: false
        ))
    }

    /// Log a UI interaction event (low frequency: clicks, selection, dialog open/close).
    func logUI(_ message: String, detail: String = "") {
        append(Entry(
            timestamp: Date(),
            kind: .ui,
            method: "UI",
            summary: "◆ \(message)",
            detail: detail.isEmpty ? message : detail,
            durationMs: nil,
            isError: false
        ))
    }

    /// Log a verbose/high-frequency event (cell edits, format slider changes, re-renders).
    /// Hidden by default in the console unless "Verbose" filter is enabled.
    func logVerbose(_ message: String, detail: String = "") {
        append(Entry(
            timestamp: Date(),
            kind: .verbose,
            method: "VRB",
            summary: "· \(message)",
            detail: detail.isEmpty ? message : detail,
            durationMs: nil,
            isError: false
        ))
    }

    /// Log engine trace lines returned from the Python server in _trace arrays.
    func logEngineTrace(_ lines: [String], forPath path: String) {
        for line in lines {
            append(Entry(
                timestamp: Date(),
                kind: .engine,
                method: "ENGINE",
                summary: "⚙ \(line)",
                detail: "\(path): \(line)",
                durationMs: nil,
                isError: false
            ))
        }
    }

    /// Log a full Python traceback from a server error response.
    func logTraceback(method: String, path: String, traceback: String) {
        let lines = traceback.components(separatedBy: "\n").filter { !$0.isEmpty }
        // Log each line as a separate error entry for readability
        for line in lines {
            append(Entry(
                timestamp: Date(),
                kind: .error,
                method: "\(method) \(path)",
                summary: "⚠ \(line.trimmingCharacters(in: .whitespaces))",
                detail: traceback,  // full traceback available in detail pane
                durationMs: nil,
                isError: true
            ))
        }
    }

    func clear() {
        entries.removeAll()
    }

    private func append(_ entry: Entry) {
        entries.append(entry)
        if entries.count > maxEntries {
            entries.removeFirst(entries.count - maxEntries)
        }
    }
}

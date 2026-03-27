// DebugConsoleView.swift — Embedded debug console panel.
// Shows API call traces and app events in a code-style log.

import SwiftUI

/// Embedded bottom panel for the debug console.
struct DebugConsolePanel: View {

    @Environment(AppState.self) private var appState
    @State private var selectedEntry: DebugLog.Entry?
    @State private var filterErrors = false
    @State private var showVerbose = false
    @State private var searchText = ""
    @State private var autoScroll = true

    private var log: DebugLog { DebugLog.shared }

    private var filteredEntries: [DebugLog.Entry] {
        var entries = log.entries
        if !showVerbose {
            entries = entries.filter { !$0.isVerbose }
        }
        if filterErrors {
            entries = entries.filter { $0.isError }
        }
        if !searchText.isEmpty {
            entries = entries.filter {
                $0.summary.localizedCaseInsensitiveContains(searchText) ||
                $0.method.localizedCaseInsensitiveContains(searchText)
            }
        }
        return entries
    }

    var body: some View {
        VStack(spacing: 0) {
            // Console toolbar
            consoleToolbar

            Divider()

            // Console content: log list + detail
            HStack(spacing: 0) {
                logList
                    .frame(minWidth: 400)

                Rectangle()
                    .fill(Color(nsColor: .separatorColor))
                    .frame(width: 1)

                detailPane
                    .frame(minWidth: 250)
            }
        }
        .background(Color(nsColor: .textBackgroundColor))
    }

    // MARK: - Console Toolbar

    private var consoleToolbar: some View {
        HStack(spacing: 8) {
            Image(systemName: "terminal.fill")
                .foregroundStyle(.green)
                .font(.system(size: 11))

            Text("Debug Console")
                .font(.system(size: 11, weight: .semibold, design: .monospaced))

            Text("(\(log.entries.count) entries)")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.secondary)

            Spacer()

            Toggle("Errors", isOn: $filterErrors)
                .toggleStyle(.checkbox)
                .controlSize(.mini)
                .font(.system(size: 10))

            Toggle("Verbose", isOn: $showVerbose)
                .toggleStyle(.checkbox)
                .controlSize(.mini)
                .font(.system(size: 10))
                .help("Show high-frequency events (cell edits, format changes, re-renders)")

            TextField("Filter", text: $searchText)
                .textFieldStyle(.roundedBorder)
                .font(.system(size: 10))
                .frame(width: 120)

            Button {
                log.clear()
                selectedEntry = nil
            } label: {
                Image(systemName: "trash")
                    .font(.system(size: 10))
            }
            .buttonStyle(.borderless)
            .help("Clear log")
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color(nsColor: .controlBackgroundColor))
    }

    // MARK: - Log List

    private var logList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(filteredEntries) { entry in
                        logRow(entry)
                            .id(entry.id)
                            .onTapGesture { selectedEntry = entry }
                            .background(selectedEntry?.id == entry.id
                                ? Color.accentColor.opacity(0.15)
                                : Color.clear)
                    }
                }
            }
            .onChange(of: log.entries.count) { _, _ in
                if autoScroll, let last = filteredEntries.last {
                    withAnimation {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    private func logRow(_ entry: DebugLog.Entry) -> some View {
        HStack(spacing: 0) {
            // Timestamp
            Text(entry.timestampString)
                .frame(width: 80, alignment: .leading)
                .foregroundStyle(.secondary)

            // Kind badge
            Text(entry.kind.rawValue)
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .padding(.horizontal, 3)
                .padding(.vertical, 1)
                .background(badgeColor(entry.kind).opacity(0.25))
                .foregroundStyle(badgeColor(entry.kind))
                .clipShape(RoundedRectangle(cornerRadius: 2))

            Text(" ")
                .frame(width: 4)

            // Summary
            Text(entry.summary)
                .lineLimit(1)
                .truncationMode(.tail)
                .foregroundStyle(entry.isError ? .red : .primary)

            Spacer()

            // Duration
            if let ms = entry.durationMs {
                Text("\(ms)ms")
                    .foregroundStyle(ms > 1000 ? Color.orange : Color.gray)
                    .frame(width: 50, alignment: .trailing)
            }
        }
        .font(.system(size: 11, design: .monospaced))
        .padding(.horizontal, 8)
        .padding(.vertical, 2)
    }

    private func badgeColor(_ kind: DebugLog.Entry.Kind) -> Color {
        switch kind {
        case .request:  return .blue
        case .response: return .green
        case .error:    return .red
        case .app:      return .purple
        case .engine:   return .orange
        case .ui:       return .teal
        case .verbose:  return .gray
        }
    }

    // MARK: - Detail Pane

    private var detailPane: some View {
        VStack(alignment: .leading, spacing: 0) {
            if let entry = selectedEntry {
                // Header
                HStack {
                    Text(entry.method)
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                    Spacer()
                    if let ms = entry.durationMs {
                        Text("\(ms)ms")
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(entry.detail, forType: .string)
                    } label: {
                        Image(systemName: "doc.on.doc")
                            .font(.system(size: 10))
                    }
                    .buttonStyle(.borderless)
                    .help("Copy to clipboard")
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color(nsColor: .controlBackgroundColor))

                Divider()

                // Body
                ScrollView {
                    Text(entry.detail)
                        .font(.system(size: 10, design: .monospaced))
                        .textSelection(.enabled)
                        .padding(6)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            } else {
                VStack {
                    Spacer()
                    Text("Select an entry")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            }
        }
    }
}

// Conform Entry to Hashable for selection
extension DebugLog.Entry: Hashable, Equatable {
    static func == (lhs: DebugLog.Entry, rhs: DebugLog.Entry) -> Bool {
        lhs.id == rhs.id
    }
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}

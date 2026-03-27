// ToolbarBanner.swift — Prism-style toolbar ribbon at the top of the window.
// Organized to match GraphPad Prism's ribbon layout.
// Active buttons are colored; unimplemented ones are grayed out.

import SwiftUI
import UniformTypeIdentifiers
import RefractionRenderer

struct ToolbarBanner: View {

    @Environment(AppState.self) private var appState
    @Environment(\.openWindow) private var openWindow

    // Dialog state
    @State private var showNewDataTableDialog = false
    @State private var showNewGraphDialog = false
    @State private var showAnalyzeDialog = false
    @State private var showDeleteConfirm = false
    @State private var showExportDialog = false
    @State private var showStatsWiki = false
    @State private var showArchitectureGuide = false
    @State private var showFormatGraph = false
    @State private var showFormatAxes = false
    @State private var showDataSettings = false
    @State private var showStatsSettings = false
    @State private var showStyleSettings = false

    var body: some View {
        HStack(spacing: 0) {
            fileGroup
            divider
            sheetGroup
            divider
            undoGroup
            divider
            clipboardGroup
            divider
            analysisGroup
            divider
            formatGroup
            divider
            insertGroup

            Spacer()

            viewGroup
            divider
            statsGroup
            divider
            exportGroup
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 2)
        .background(.bar)
        .overlay(alignment: .bottom) {
            Divider()
        }
        // Dialogs
        .sheet(isPresented: $showNewDataTableDialog) {
            NewDataTableDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showNewGraphDialog) {
            NewGraphDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showAnalyzeDialog) {
            AnalyzeDataDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showStatsWiki) {
            StatsWikiDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showArchitectureGuide) {
            ArchitectureGuideDialog()
        }
        .sheet(isPresented: $showExportDialog) {
            if let graph = appState.activeGraph, let spec = graph.chartSpec {
                ExportChartDialog(spec: spec, graphLabel: graph.label)
            }
        }
        .sheet(isPresented: $showFormatGraph) {
            if let graph = appState.activeGraph {
                FormatGraphDialog(settings: graph.formatSettings)
                    .environment(appState)
            }
        }
        .sheet(isPresented: $showFormatAxes) {
            if let graph = appState.activeGraph {
                FormatAxesDialog(settings: graph.formatAxesSettings)
                    .environment(appState)
            }
        }
        .sheet(isPresented: $showDataSettings) {
            DataSettingsDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showStatsSettings) {
            StatsSettingsDialog()
                .environment(appState)
        }
        .sheet(isPresented: $showStyleSettings) {
            StyleSettingsDialog()
                .environment(appState)
        }
        .alert("Delete Selected Item?", isPresented: $showDeleteConfirm) {
            Button("Delete", role: .destructive) {
                deleteSelectedItem()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This action cannot be undone.")
        }
    }

    // MARK: - File Group

    private var fileGroup: some View {
        VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "doc.badge.plus", label: "New", color: .blue) {
                    openWindow(id: "main")
                }
                Menu {
                    Button("Open File...") {
                        Task { await appState.openProjectFile() }
                    }

                    Divider()

                    if RecentFiles.shared.paths.isEmpty {
                        Text("No Recent Files")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(RecentFiles.shared.paths, id: \.self) { url in
                            Button(url.lastPathComponent) {
                                Task { await appState.loadProjectFromURL(url) }
                            }
                        }

                        Divider()

                        Button("Clear List") {
                            RecentFiles.shared.clear()
                        }
                    }
                } label: {
                    VStack(spacing: 1) {
                        Image(systemName: "folder")
                            .font(.system(size: 14))
                            .frame(width: 20, height: 18)
                        Text("Open")
                            .font(.system(size: 8))
                            .lineLimit(1)
                    }
                    .frame(minWidth: 32)
                }
                .menuStyle(.borderlessButton)
                .foregroundStyle(.orange)
                activeButton(icon: "square.and.arrow.down", label: "Save", color: .green) {
                    Task { await appState.saveProjectFile() }
                }
            }
            groupLabel("File")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Sheet Group

    private var sheetGroup: some View {
        let hasExperiment = appState.activeExperiment != nil
        let hasData = appState.activeExperiment?.hasData ?? false
        let hasSelection = appState.activeItemID != nil

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "tablecells.badge.ellipsis", label: "Table", color: hasExperiment ? .teal : .gray) {
                    guard appState.activeExperiment != nil else { return }
                    DebugLog.shared.logUI("open NewDataTableDialog")
                    showNewDataTableDialog = true
                }
                activeButton(icon: "chart.bar.fill", label: "Graph", color: hasData ? .indigo : .gray) {
                    guard appState.activeExperiment?.hasData == true else { return }
                    DebugLog.shared.logUI("open NewGraphDialog")
                    showNewGraphDialog = true
                }
                activeButton(icon: "trash", label: "Delete", color: hasSelection ? .red : .gray) {
                    guard appState.activeItemID != nil else { return }
                    DebugLog.shared.logUI("delete \(appState.activeItemKind?.rawValue ?? "item")")
                    showDeleteConfirm = true
                }
            }
            groupLabel("Sheet")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Undo Group

    private var undoGroup: some View {
        VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "arrow.uturn.backward", label: "Undo",
                             color: appState.canUndo ? .blue : .gray) {
                    let desc = appState.undoManager.undoActionName
                    appState.undoManager.undo()
                    appState.refreshUndoState()
                    DebugLog.shared.logUI("undo: \(desc.isEmpty ? "(empty)" : desc)")
                }
                .disabled(!appState.canUndo)

                activeButton(icon: "arrow.uturn.forward", label: "Redo",
                             color: appState.canRedo ? .blue : .gray) {
                    let desc = appState.undoManager.redoActionName
                    appState.undoManager.redo()
                    appState.refreshUndoState()
                    DebugLog.shared.logUI("redo: \(desc.isEmpty ? "(empty)" : desc)")
                }
                .disabled(!appState.canRedo)
            }
            groupLabel("Undo")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Clipboard Group

    private var clipboardGroup: some View {
        let hasChart = appState.activeGraph?.chartSpec != nil

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "doc.on.doc", label: "Copy", color: hasChart ? .mint : .gray) {
                    copyChartToClipboard()
                }
            }
            groupLabel("Clipboard")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Analysis Group

    private var analysisGroup: some View {
        let hasData = appState.activeExperiment?.hasData ?? false

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "function", label: "Analyze", color: hasData ? .purple : .gray) {
                    guard appState.activeExperiment?.hasData == true else { return }
                    DebugLog.shared.logUI("open AnalyzeDataDialog")
                    showAnalyzeDialog = true
                }
            }
            groupLabel("Analysis")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Format Group (NEW)

    private var formatGroup: some View {
        let hasGraph = appState.activeGraph != nil

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "doc.fill", label: "Data", color: hasGraph ? .teal : .gray) {
                    guard appState.activeGraph != nil else { return }
                    DebugLog.shared.logUI("open DataSettingsDialog")
                    showDataSettings = true
                }
                activeButton(icon: "paintbrush", label: "Format", color: hasGraph ? .orange : .gray) {
                    guard appState.activeGraph != nil else { return }
                    DebugLog.shared.logUI("open FormatGraphDialog")
                    showFormatGraph = true
                }
                activeButton(icon: "ruler", label: "Axes", color: hasGraph ? .brown : .gray) {
                    guard appState.activeGraph != nil else { return }
                    DebugLog.shared.logUI("open FormatAxesDialog")
                    showFormatAxes = true
                }
                activeButton(icon: "paintpalette", label: "Style", color: hasGraph ? .yellow : .gray) {
                    guard appState.activeGraph != nil else { return }
                    DebugLog.shared.logUI("open StyleSettingsDialog")
                    showStyleSettings = true
                }
                activeButton(icon: "function", label: "Stats", color: hasGraph ? .purple : .gray) {
                    guard appState.activeGraph != nil else { return }
                    DebugLog.shared.logUI("open StatsSettingsDialog")
                    showStatsSettings = true
                }
            }
            groupLabel("Format")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Insert Group (NEW — annotations)

    private var insertGroup: some View {
        let hasGraph = appState.activeGraph?.chartSpec != nil

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                disabledButton(icon: "textformat", label: "Text")
                disabledButton(icon: "line.diagonal", label: "Line")
                disabledButton(icon: "bracket", label: "Bracket")
            }
            groupLabel("Insert")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - View Group (NEW — zoom)

    private var viewGroup: some View {
        VStack(spacing: 1) {
            HStack(spacing: 6) {
                disabledButton(icon: "plus.magnifyingglass", label: "Zoom In")
                disabledButton(icon: "minus.magnifyingglass", label: "Zoom Out")
                disabledButton(icon: "arrow.up.left.and.arrow.down.right", label: "Fit")
            }
            groupLabel("View")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Stats Group

    private var statsGroup: some View {
        VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "book.fill", label: "Wiki", color: .cyan) {
                    DebugLog.shared.logUI("open StatsWiki")
                    showStatsWiki = true
                }
                activeButton(icon: "text.book.closed", label: "Guide", color: .indigo) {
                    DebugLog.shared.logUI("open ArchitectureGuide")
                    showArchitectureGuide = true
                }
            }
            groupLabel("Reference")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Export Group

    private var exportGroup: some View {
        let hasChart = appState.activeGraph?.chartSpec != nil

        return VStack(spacing: 1) {
            HStack(spacing: 6) {
                activeButton(icon: "square.and.arrow.up", label: "Export", color: hasChart ? .pink : .gray) {
                    guard appState.activeGraph?.chartSpec != nil else { return }
                    DebugLog.shared.logUI("open ExportDialog")
                    showExportDialog = true
                }
            }
            groupLabel("Export")
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Button Builders

    private func activeButton(icon: String, label: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 1) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .frame(width: 20, height: 18)
                Text(label)
                    .font(.system(size: 8))
                    .lineLimit(1)
            }
            .frame(minWidth: 32)
        }
        .buttonStyle(.plain)
        .foregroundStyle(color)
    }

    private func disabledButton(icon: String, label: String) -> some View {
        VStack(spacing: 1) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .frame(width: 20, height: 18)
            Text(label)
                .font(.system(size: 8))
                .lineLimit(1)
        }
        .frame(minWidth: 32)
        .foregroundStyle(.quaternary)
    }

    private func groupLabel(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 8, weight: .medium))
            .foregroundStyle(.tertiary)
    }

    private var divider: some View {
        Rectangle()
            .fill(Color.gray.opacity(0.2))
            .frame(width: 1, height: 40)
            .padding(.horizontal, 2)
    }

    // MARK: - Actions

    private func deleteSelectedItem() {
        guard let kind = appState.activeItemKind,
              let id = appState.activeItemID else { return }
        switch kind {
        case .dataTable:
            appState.removeDataTable(id: id)
        case .graph:
            appState.removeGraph(id: id)
        case .analysis:
            appState.removeAnalysis(id: id)
        }
    }

    private func copyChartToClipboard() {
        guard let graph = appState.activeGraph,
              let spec = graph.chartSpec else { return }

        let renderer = ImageRenderer(content:
            ChartCanvasView(spec: spec)
                .frame(width: 800, height: 600)
        )
        renderer.scale = 2.0

        guard let image = renderer.nsImage else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.writeObjects([image])

        DebugLog.shared.logAppEvent("copyChartToClipboard()", detail: "Copied \(graph.label) as image")
    }
}

// ContentView.swift — Root view with permanent sidebar + toolbar banner.
// Debug console panel embedded at bottom when developer mode is on.

import SwiftUI

struct ContentView: View {

    @Environment(AppState.self) private var appState
    @Environment(PythonServer.self) private var server

    @State private var sidebarWidth: CGFloat = 240
    @State private var consoleHeight: CGFloat = 220

    var body: some View {
        VStack(spacing: 0) {
            // Prism-style toolbar banner
            ToolbarBanner()

            // Main area + optional debug console
            VStack(spacing: 0) {
                // Main content: fixed sidebar + detail
                HStack(spacing: 0) {
                    // Left: permanent navigator sidebar
                    NavigatorView()
                        .frame(width: sidebarWidth)
                        .background(Color(nsColor: .controlBackgroundColor))

                    // Draggable divider
                    Rectangle()
                        .fill(Color(nsColor: .separatorColor))
                        .frame(width: 1)
                        .onHover { hovering in
                            if hovering {
                                NSCursor.resizeLeftRight.push()
                            } else {
                                NSCursor.pop()
                            }
                        }
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    let newWidth = sidebarWidth + value.translation.width
                                    sidebarWidth = min(max(newWidth, 180), 400)
                                }
                        )

                    // Right: active item content
                    contentArea
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }

                // Debug console panel (embedded at bottom)
                if appState.developerMode {
                    // Draggable console divider
                    Rectangle()
                        .fill(Color(nsColor: .separatorColor))
                        .frame(height: 1)
                        .onHover { hovering in
                            if hovering {
                                NSCursor.resizeUpDown.push()
                            } else {
                                NSCursor.pop()
                            }
                        }
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    let newHeight = consoleHeight - value.translation.height
                                    consoleHeight = min(max(newHeight, 100), 500)
                                }
                        )

                    DebugConsolePanel()
                        .frame(height: consoleHeight)
                }
            }
        }
        .alert("Save Current Project?", isPresented: Bindable(appState).showNewProjectConfirm) {
            Button("Save") {
                Task {
                    await appState.saveProjectFile()
                    appState.newProject()
                }
            }
            Button("Don\u{2019}t Save", role: .destructive) {
                appState.newProject()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("You have unsaved changes. Would you like to save before creating a new project?")
        }
        .onChange(of: appState.projectDisplayName) { _, newTitle in
            NSApplication.shared.mainWindow?.title = newTitle
        }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                NSApplication.shared.mainWindow?.title = appState.projectDisplayName
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        appState.developerMode.toggle()
                    }
                } label: {
                    Image(systemName: appState.developerMode ? "terminal.fill" : "terminal")
                        .foregroundStyle(appState.developerMode ? .green : .secondary)
                }
                .help(appState.developerMode ? "Hide Debug Console" : "Show Debug Console")

                if appState.developerMode {
                    serverStatusIndicator
                }
            }
        }
    }

    // MARK: - Content area: dispatch by item kind

    @ViewBuilder
    private var contentArea: some View {
        if let error = appState.error {
            ErrorView(
                errorMessage: error,
                onRetry: {
                    Task { await appState.retryLastAction() }
                },
                onDismiss: {
                    appState.dismissError()
                }
            )
        } else if let kind = appState.activeItemKind {
            switch kind {
            case .dataTable:
                DataTableView()
            case .graph:
                if let graph = appState.activeGraph {
                    GraphSheetView(graph: graph)
                } else {
                    emptyCanvas
                }
            case .analysis:
                if let analysis = appState.activeAnalysis {
                    ResultsSheetView(analysis: analysis)
                } else {
                    emptyCanvas
                }
            }
        } else {
            emptyCanvas
        }
    }

    /// Blank canvas — shown when nothing is selected.
    private var emptyCanvas: some View {
        Color(nsColor: .windowBackgroundColor)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Server status

    @ViewBuilder
    private var serverStatusIndicator: some View {
        switch server.state {
        case .idle:
            Label("Server idle", systemImage: "circle")
                .foregroundStyle(.secondary)
                .labelStyle(.iconOnly)
        case .starting:
            ProgressView()
                .controlSize(.small)
                .help("Starting Python server...")
        case .running:
            Image(systemName: "circle.fill")
                .foregroundStyle(.green)
                .help("Python server running on port \(PythonServer.port)")
        case .failed(let msg):
            Image(systemName: "exclamationmark.circle.fill")
                .foregroundStyle(.red)
                .help("Server failed: \(msg)")
        }
    }
}
